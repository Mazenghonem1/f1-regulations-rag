"""Exact cosine-similarity dense retriever (ADR 0001) -- no FAISS.

At ~1700 chunks x 384 dims the embedding matrix is a few MB; an exact
cosine search is one matrix-vector product, sub-millisecond, and more
accurate than an approximate index since there's no approximation.
"""
import numpy as np

from .embed import embed_chunks, embed_query


class DenseRetriever:
    """Retriever interface: `.search(query, k) -> list[(chunk_id, score)]`,
    ranked descending by score. Narrow enough that FAISS (or anything else)
    could replace this without touching callers (ADR 0001)."""

    def __init__(self, chunks: list[dict]):
        self.chunk_ids = [c["chunk_id"] for c in chunks]
        self.embeddings = embed_chunks(chunks)  # (N, D), rows pre-normalised

    def search(self, query: str, k: int = 20) -> list[tuple[str, float]]:
        q = embed_query(query)  # (D,), pre-normalised
        scores = self.embeddings @ q  # cosine similarity, since both are unit-norm
        top_idx = np.argsort(-scores)[:k]
        return [(self.chunk_ids[i], float(scores[i])) for i in top_idx]
