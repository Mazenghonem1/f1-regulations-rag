"""Divergent Precedent detector (CONTEXT.md): two or more Decisions citing
the same Article on materially similar incidents, reaching different
Outcomes. Suppressed by Justified Distinction evidence (ADR 0002) -- this is
the precision half, built in the same phase as the detector, not after.

Sharing a cited Article is not "materially similar" on its own -- Article
12.2.1 alone covers unrelated incident types (unsafe driving, delta-time
compliance, impeding) across completely different events, and comparing
every pair of Decisions that merely cite the same Article floods the
detector with unrelated pairs (verified: 1285 raw pairs on this corpus,
0% naturally suppressed, because there's nothing in common to suppress).
A Fact-text similarity gate is the "materially similar incident" check
CONTEXT.md asks for, ahead of the Mitigating Factor suppression check.
"""
import re
from itertools import combinations

import numpy as np

from ..index.embed import embed_texts
from .mitigating import is_justified_distinction

SIMILARITY_THRESHOLD = 0.75

# "(N seconds added to elapsed Race/Sprint time)" is a boilerplate clause
# some Decision PDFs append and others omit for the identical penalty --
# verified false positives (q05/q38): "5 second time penalty." and
# "5 second time penalty. (5 seconds added to elapsed Race time)." are
# the same Outcome. Penalty-points text is NOT stripped -- that is a real
# difference in what was imposed, not phrasing noise.
_ADDED_TO_ELAPSED_RE = re.compile(
    r"\.?\s*\(\d+\s+seconds?\s+added\s+to\s+elapsed\s+[^)]*\)\.?", re.IGNORECASE
)


def _normalise_outcome(outcome: str) -> str:
    """Strip the "(N seconds added to elapsed ... time)" boilerplate clause
    and trailing punctuation -- "5 second time penalty" and "5 second time
    penalty. (5 seconds added to elapsed Race time)." are the same Outcome,
    not a divergence (verified: this exact pair appeared as a spurious flag
    on a real query, purely from inconsistent trailing periods and an
    optional restatement clause in the source PDFs)."""
    stripped = _ADDED_TO_ELAPSED_RE.sub("", outcome)
    return stripped.strip().lower().rstrip(".")


def _outcomes_differ(a: dict, b: dict) -> bool:
    oa, ob = _normalise_outcome(a.get("outcome") or ""), _normalise_outcome(b.get("outcome") or "")
    return bool(oa) and bool(ob) and oa != ob


def _fact_vectors(group: list[dict]) -> dict[str, np.ndarray]:
    """Embed every Decision's Fact text in one Article group as a single
    batch, not once per pair -- combinations(group, 2) with a per-pair
    embed call is minutes-slow on a busy Article like 33.3 (verified)."""
    with_fact = [d for d in group if d.get("fact")]
    if not with_fact:
        return {}
    vectors = embed_texts([d["fact"] for d in with_fact])
    return {d["chunk_id"]: vec for d, vec in zip(with_fact, vectors)}


def detect_divergent_precedent(decisions: list[dict]) -> list[dict]:
    """`decisions` are the Decision-type chunks among a retrieved set (already
    filtered to doc_type == "decision" by the caller). Groups by shared cited
    Article, gates each pair on Fact-text similarity ("materially similar
    incidents"), compares Outcomes, and flags unless Justified Distinction
    evidence suppresses it.

    Returns a list of flags: {type, article, decisions: [chunk_id, chunk_id],
    outcomes: [str, str], similarity: float, suppressed: bool, evidence:
    [str]}. Suppressed flags are included (not silently dropped) so
    precision can be measured against them -- a caller only surfaces
    `suppressed is False` flags."""
    by_article: dict[str, list[dict]] = {}
    for d in decisions:
        for article in d.get("cited_articles") or []:
            by_article.setdefault(article, []).append(d)

    flags = []
    for article, group in by_article.items():
        vectors = _fact_vectors(group)
        for a, b in combinations(group, 2):
            if a["chunk_id"] == b["chunk_id"]:
                continue
            if not _outcomes_differ(a, b):
                continue
            vec_a, vec_b = vectors.get(a["chunk_id"]), vectors.get(b["chunk_id"])
            if vec_a is None or vec_b is None:
                continue
            similarity = float(np.dot(vec_a, vec_b))
            if similarity < SIMILARITY_THRESHOLD:
                continue
            suppressed, evidence = is_justified_distinction(a, b)
            flags.append(
                {
                    "type": "divergent_precedent",
                    "article": article,
                    "decisions": [a["chunk_id"], b["chunk_id"]],
                    "outcomes": [a.get("outcome"), b.get("outcome")],
                    "similarity": similarity,
                    "suppressed": suppressed,
                    "evidence": evidence,
                }
            )
    return flags
