"""Hybrid retrieval entrypoint: BM25 + dense, fused by RRF, optionally
reranked. The eval harness needs both configurations, so `use_reranker`
is a plain switch rather than two separate call paths.
"""
import pathlib

from ..rerank.rerank import rerank
from .bm25_retriever import BM25Retriever
from .corpus import load_corpus
from .dense import DenseRetriever
from .fuse import reciprocal_rank_fusion

RESULTS_DIR = pathlib.Path("results")


class Retriever:
    """Owns the corpus and both retrievers; built once, queried many times
    (embedding the corpus is the slow part -- do it once per process)."""

    def __init__(self, chunks: list[dict] | None = None):
        self.chunks = chunks if chunks is not None else load_corpus()
        self.by_id = {c["chunk_id"]: c for c in self.chunks}
        self.dense = DenseRetriever(self.chunks)
        self.bm25 = BM25Retriever(self.chunks)

    def retrieve(
        self, query: str, fused_k: int = 20, top_n: int = 8, use_reranker: bool = True
    ) -> dict:
        """Return {"chunks": [chunk dict...], "pre_rerank_order": [...],
        "post_rerank_order": [...] or None}. `chunks` is the final ranked
        list handed to contradiction-detection/generation -- top_n after
        reranking, or the fused top_n if reranking is off."""
        dense_hits = self.dense.search(query, k=fused_k)
        bm25_hits = self.bm25.search(query, k=fused_k)
        fused = reciprocal_rank_fusion([dense_hits, bm25_hits], k=fused_k)

        if not use_reranker:
            top = fused[:top_n]
            return {
                "chunks": [self.by_id[cid] for cid, _score in top],
                "pre_rerank_order": [cid for cid, _s in fused],
                "post_rerank_order": None,
            }

        candidates = [(cid, self.by_id[cid]["text"]) for cid, _score in fused]
        result = rerank(query, candidates, top_n=top_n)
        return {
            "chunks": [self.by_id[cid] for cid, _score in result["reranked"]],
            "pre_rerank_order": result["pre_rerank_order"],
            "post_rerank_order": result["post_rerank_order"],
        }


def log_query(query: str, result: dict, run_name: str = "manual") -> None:
    """Append one retrieval result to results/retrieval_log.jsonl -- every
    retrieved chunk id and the rerank order delta, reproducible per run."""
    import json

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    entry = {
        "run": run_name,
        "query": query,
        "chunk_ids": [c["chunk_id"] for c in result["chunks"]],
        "pre_rerank_order": result["pre_rerank_order"],
        "post_rerank_order": result["post_rerank_order"],
    }
    with (RESULTS_DIR / "retrieval_log.jsonl").open("a") as f:
        f.write(json.dumps(entry) + "\n")
