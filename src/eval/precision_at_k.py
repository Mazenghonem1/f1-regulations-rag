"""Retrieval precision@k: does at least one gold chunk_id appear in the
top-k retrieved chunks. Computed with and without reranking so the delta
is a reportable eval result (PLAN.md).

Questions with no gold_chunk_ids (open-ended seeded contradictions, where
several valid pairs exist -- see eval_set.json's q08/q09/q10/q32 notes) are
skipped, since there's no fixed ground truth to score precision against.
"""


def precision_at_k(retriever, questions: list[dict], k: int, use_reranker: bool) -> dict:
    """Returns {"precision": float, "scored": int, "skipped": int, "per_question": [...]}."""
    scored = []
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

    precision = sum(s["hit"] for s in scored) / len(scored) if scored else 0.0
    return {
        "precision": precision,
        "scored": len(scored),
        "skipped": skipped,
        "per_question": scored,
    }
