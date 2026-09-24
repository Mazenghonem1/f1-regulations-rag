"""Retrieval precision@k: does at least one gold chunk_id appear in the
top-k retrieved chunks. Computed with and without reranking so the delta
is a reportable eval result (PLAN.md).

Questions with no gold_chunk_ids (open-ended seeded contradictions, where
several valid pairs exist -- see eval_set.json's q08/q09/q10/q32 notes) are
skipped, since there's no fixed ground truth to score precision against.
"""
import re

# A regulation chunk_id is "reg:{season}:{kind}:{issue}:{article_id}" -- the
# corpus keeps every historical Issue of every amended Article as its own
# chunk (by design, for observable change history), so heavily-amended
# Articles have 18-20 near-duplicate chunks competing for rank. Verified:
# 9 of precision@8's 11 real misses retrieve the exact right Article, just a
# different Issue than the one gold_chunk_ids happens to pin -- a real
# retrieval success the exact-match metric can't see. "Article family"
# (kind + article_id, ignoring season/issue) is what "any Issue answers
# this" means.
_YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")


def _article_family(chunk_id: str) -> tuple[str, str] | None:
    if not chunk_id.startswith("reg:"):
        return None
    parts = chunk_id.split(":")
    return (parts[2], parts[4])


def _families(gold: set[str]) -> set[tuple[str, str]]:
    families = {_article_family(g) for g in gold}
    families.discard(None)
    return families


def precision_at_k(retriever, questions: list[dict], k: int, use_reranker: bool) -> dict:
    """Returns {"precision": float, "scored": int, "skipped": int,
    "per_question": [...], "article_level": {...}}.

    "article_level" is a second, more forgiving metric: a hit if *any*
    Issue of the gold Article is retrieved, not just the pinned one -- but
    only for questions whose text doesn't name a specific year (e.g. "2023
    FIA... Regulations", "between 2023 Issues 6 and 7"), since crediting
    any Issue would be wrong for a question genuinely asking about one
    season's wording. This never changes precision@k itself; both numbers
    are reported side by side."""
    scored = []
    article_scored = []
    skipped = 0
    for q in questions:
        gold = set(q.get("gold_chunk_ids") or [])
        if not gold:
            skipped += 1
            continue
        result = retriever.retrieve(q["question"], top_n=k, use_reranker=use_reranker)
        retrieved_ids = {c["chunk_id"] for c in result["chunks"]}
        hit = bool(gold & retrieved_ids)
        scored.append({"id": q["id"], "hit": hit})

        if not _YEAR_RE.search(q["question"]):
            gold_families = _families(gold)
            if gold_families:
                retrieved_families = _families(retrieved_ids)
                article_hit = bool(gold_families & retrieved_families) or hit
                article_scored.append({"id": q["id"], "hit": article_hit})

    precision = sum(s["hit"] for s in scored) / len(scored) if scored else 0.0
    article_precision = (
        sum(s["hit"] for s in article_scored) / len(article_scored) if article_scored else None
    )
    return {
        "precision": precision,
        "scored": len(scored),
        "skipped": skipped,
        "per_question": scored,
        "article_level": {
            "precision": article_precision,
            "scored": len(article_scored),
            "per_question": article_scored,
        },
    }
