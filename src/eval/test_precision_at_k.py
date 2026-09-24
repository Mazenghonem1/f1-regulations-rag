"""Check for precision_at_k's article-level metric: credits any Issue of
the gold Article, but only for questions that don't name a specific year --
found while investigating why 9 of 11 real precision@8 misses retrieve the
exact right Article, just a different historical Issue than gold_chunk_ids
happens to pin.

Run: python -m src.eval.test_precision_at_k
"""
from .precision_at_k import precision_at_k


class _FakeRetriever:
    """Returns a fixed chunk list regardless of query -- precision_at_k only
    needs chunk_id, so a minimal stub is enough."""

    def __init__(self, chunk_ids):
        self._chunks = [{"chunk_id": c} for c in chunk_ids]

    def retrieve(self, query, top_n, use_reranker):
        return {"chunks": self._chunks[:top_n]}


# wrong Issue of the right Article -- exact miss, but a real article-level hit
retriever = _FakeRetriever(["reg:2024:sporting:2:48", "reg:2024:sporting:3:48"])
questions = [
    {
        "id": "q_wrong_issue",
        "question": "What penalty applies to an incorrect grid location?",
        "gold_chunk_ids": ["reg:2023:sporting:1:48"],
    }
]
result = precision_at_k(retriever, questions, k=8, use_reranker=True)
assert result["precision"] == 0.0, result
assert result["article_level"]["precision"] == 1.0, result["article_level"]

# a question naming a specific year is NOT eligible for article-level credit
# -- q11's real case: asks about "2023" specifically, wrong Issue must stay a miss
questions_year = [
    {
        "id": "q_year_specific",
        "question": "What does Article 33.3 of the 2023 FIA Sporting Regulations say?",
        "gold_chunk_ids": ["reg:2023:sporting:1:33"],
    }
]
retriever_wrong_issue = _FakeRetriever(["reg:2024:sporting:1:33"])
result = precision_at_k(retriever_wrong_issue, questions_year, k=8, use_reranker=True)
assert result["precision"] == 0.0, result
assert result["article_level"]["scored"] == 0, result["article_level"]

# an exact hit also counts as an article-level hit (never double-penalised)
retriever_exact = _FakeRetriever(["reg:2023:sporting:1:48"])
result = precision_at_k(retriever_exact, questions, k=8, use_reranker=True)
assert result["precision"] == 1.0, result
assert result["article_level"]["precision"] == 1.0, result["article_level"]

# a genuinely wrong Article is a miss on both metrics
retriever_wrong_article = _FakeRetriever(["reg:2023:sporting:1:12"])
result = precision_at_k(retriever_wrong_article, questions, k=8, use_reranker=True)
assert result["precision"] == 0.0, result
assert result["article_level"]["precision"] == 0.0, result["article_level"]

# Decision-only gold (no "reg:" chunks) is excluded from article_level, not
# crashed on or silently miscounted
questions_decision = [
    {
        "id": "q_decision",
        "question": "What happened in that Decision?",
        "gold_chunk_ids": ["dec:2023:Qatar Grand Prix:70"],
    }
]
result = precision_at_k(_FakeRetriever(["dec:2023:Qatar Grand Prix:70"]), questions_decision, k=8, use_reranker=True)
assert result["article_level"]["scored"] == 0, result["article_level"]

print("OK — article-level precision credits any Issue of the gold Article, except for year-specific questions.")
