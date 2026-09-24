"""Cross-encoder reranking of the top ~20 fused candidates down to top 5-8.

Logs pre- vs post-rerank order so the rank-change delta can be reported as
an eval result -- "reranking changed the top result in X% of queries" needs
the before/after orderings, not just the final list.
"""
from sentence_transformers import CrossEncoder

MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"

_model: CrossEncoder | None = None


def _get_model() -> CrossEncoder:
    global _model
    if _model is None:
        _model = CrossEncoder(MODEL_NAME)
    return _model


def rerank(
    query: str, candidates: list[tuple[str, str]], top_n: int = 8
) -> dict:
    """`candidates` is [(chunk_id, text)] in pre-rerank order (e.g. RRF
    output). Returns {"reranked": [(chunk_id, score)] top_n, "pre_rerank_order":
    [chunk_id...], "post_rerank_order": [chunk_id...]} -- the two order lists
    are what the eval harness diffs to measure rank change."""
    if not candidates:
        return {"reranked": [], "pre_rerank_order": [], "post_rerank_order": []}

    model = _get_model()
    pairs = [(query, text) for _chunk_id, text in candidates]
    scores = model.predict(pairs)

    pre_order = [chunk_id for chunk_id, _text in candidates]
    scored = list(zip(pre_order, scores))
    scored.sort(key=lambda item: -item[1])
    post_order = [chunk_id for chunk_id, _score in scored]

    return {
        "reranked": [(chunk_id, float(score)) for chunk_id, score in scored[:top_n]],
        "pre_rerank_order": pre_order,
        "post_rerank_order": post_order,
    }
