"""Contradiction recall and precision, reported per detector (ADR 0002) --
the headline metric. Recall: of the seeded_contradiction questions, what
fraction did the system flag (unsuppressed) for the right Article. Precision:
of the negative_justified_distinction questions, what fraction did the
system correctly NOT flag.
"""
from ..contradiction.detect import detect_contradictions

# Wider than precision@8's k=8 -- a Divergent Precedent pair needs BOTH
# Decisions retrieved to be detectable at all, and the top-8 for several
# real questions (q01, q10, q32) only surfaced one half of the pair
# (verified: all 8 retrieved chunks were from a single Grand Prix in q01's
# case). This retrieval call only feeds the contradiction check, never
# generation or precision@k, so widening it here doesn't touch what an LLM
# sees or redefine "precision@8" -- it only gives the detector more
# candidates to find a real pair in.
CONTRADICTION_RETRIEVAL_TOP_N = 16


def _flagged_for_article(flags: list[dict], article: str, detector: str) -> bool:
    """Coarse fallback: is there ANY unsuppressed flag for this Article,
    regardless of which Decisions it names. Used only for questions with no
    specific gold pair to check against (q08/q09 -- deliberately open-ended,
    several valid pairs exist for the underlying controversy)."""
    for f in flags:
        if f.get("suppressed"):
            continue
        if f["type"] != detector:
            continue
        if detector == "divergent_precedent" and f["article"] == article:
            return True
        if detector == "superseded_precedent" and f["article"] == article:
            return True
    return False


def _flagged_for_pair(flags: list[dict], gold_ids: list[str], detector: str) -> bool:
    """Precise check: is the SPECIFIC pair/Decision this question names
    actually flagged (unsuppressed), not just any flag for the same Article.

    Fixes a real metric-granularity gap: widening contradiction-check
    retrieval (CONTRADICTION_RETRIEVAL_TOP_N) surfaces more candidate pairs
    overall, including genuine, unrelated Divergent Precedent flags for the
    same Article a negative question isn't about -- _flagged_for_article
    can't tell those apart from the question's own pair."""
    gold = set(gold_ids)
    for f in flags:
        if f.get("suppressed"):
            continue
        if f["type"] != detector:
            continue
        if detector == "divergent_precedent" and set(f["decisions"]) == gold:
            return True
        if detector == "superseded_precedent" and f["decision"] in gold:
            return True
    return False


def contradiction_metrics(retriever, questions: list[dict], article_changes: dict) -> dict:
    """Returns per-detector {recall, precision, tp, fn, tn, fp} plus an
    overall summary. Only questions with a `detector` field are scored
    (seeded_contradiction and negative_justified_distinction types).

    Scored against the question's specific gold_chunk_ids pair when one
    exists (divergent_precedent: exactly 2 ids, superseded_precedent:
    exactly 1) -- falls back to the coarser per-Article check only for
    questions with no fixed pair (q08/q09's deliberately open-ended
    controversies, where several valid pairs exist)."""
    by_detector: dict[str, dict[str, int]] = {}

    for q in questions:
        detector = q.get("detector")
        if not detector:
            continue
        by_detector.setdefault(detector, {"tp": 0, "fn": 0, "tn": 0, "fp": 0})

        result = retriever.retrieve(q["question"], top_n=CONTRADICTION_RETRIEVAL_TOP_N, use_reranker=True)
        flags = detect_contradictions(result["chunks"], article_changes)

        gold_ids = q.get("gold_chunk_ids") or []
        expected_len = 2 if detector == "divergent_precedent" else 1
        if len(gold_ids) == expected_len:
            flagged = _flagged_for_pair(flags, gold_ids, detector)
        else:
            flagged = _flagged_for_article(flags, q["gold_article"], detector)

        expected = q["expected_flag"]
        counts = by_detector[detector]
        if expected and flagged:
            counts["tp"] += 1
        elif expected and not flagged:
            counts["fn"] += 1
        elif not expected and not flagged:
            counts["tn"] += 1
        else:
            counts["fp"] += 1

    summary = {}
    for detector, counts in by_detector.items():
        tp, fn, tn, fp = counts["tp"], counts["fn"], counts["tn"], counts["fp"]
        recall = tp / (tp + fn) if (tp + fn) else None
        precision = tp / (tp + fp) if (tp + fp) else None
        summary[detector] = {**counts, "recall": recall, "precision": precision}
    return summary
