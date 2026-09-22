"""Reciprocal rank fusion: combine ranked lists from independent retrievers
into one ranking, without needing their scores to be on comparable scales
(BM25 scores and cosine similarities aren't).
"""

RRF_K = 60  # standard RRF damping constant


def reciprocal_rank_fusion(
    ranked_lists: list[list[tuple[str, float]]], k: int = 20
) -> list[tuple[str, float]]:
    """Each input is a ranked [(chunk_id, score)] list (best first); score
    values are ignored, only rank matters. A retriever that returns an empty
    list contributes nothing and doesn't break the fusion. Returns the
    top-k [(chunk_id, fused_score)] fused across all lists."""
    fused: dict[str, float] = {}
    for ranked in ranked_lists:
        for rank, (chunk_id, _score) in enumerate(ranked):
            fused[chunk_id] = fused.get(chunk_id, 0.0) + 1.0 / (RRF_K + rank + 1)
    ordered = sorted(fused.items(), key=lambda item: -item[1])
    return ordered[:k]
