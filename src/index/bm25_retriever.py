"""BM25 retriever -- carries exact Article-number and driver-name lookups,
which dense embeddings handle poorly.
"""
import re

from rank_bm25 import BM25Okapi

_TOKEN_RE = re.compile(r"[a-z0-9]+(?:\.[a-z0-9]+)*")


def _tokenize(text: str) -> list[str]:
    """Lowercase, alphanumeric tokens, keeping dotted Article numbers like
    "33.3" intact as one token rather than splitting on the dot."""
    return _TOKEN_RE.findall(text.lower())


class BM25Retriever:
    """Same interface as DenseRetriever: `.search(query, k) -> list[(chunk_id, score)]`."""

    def __init__(self, chunks: list[dict]):
        self.chunk_ids = [c["chunk_id"] for c in chunks]
        tokenized = [_tokenize(c["text"]) for c in chunks]
        self.bm25 = BM25Okapi(tokenized)

    def search(self, query: str, k: int = 20) -> list[tuple[str, float]]:
        scores = self.bm25.get_scores(_tokenize(query))
        ranked = sorted(range(len(scores)), key=lambda i: -scores[i])[:k]
        return [(self.chunk_ids[i], float(scores[i])) for i in ranked]
