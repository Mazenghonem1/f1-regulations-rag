"""Check: a literal Article-number query ranks the exact Article
first (BM25 earning its place); RRF handles one retriever returning nothing.

Run: python -m src.index.test_retrieval
"""
from .bm25_retriever import BM25Retriever
from .fuse import reciprocal_rank_fusion

# RRF handles one retriever returning nothing
fused = reciprocal_rank_fusion([[("a", 0.9), ("b", 0.5)], []], k=5)
assert [cid for cid, _ in fused] == ["a", "b"], fused

# RRF ranks an item first only when it comes first in both underlying lists
fused = reciprocal_rank_fusion(
    [[("a", 0.9), ("b", 0.5)], [("a", 5.0), ("c", 1.0)]], k=5
)
assert fused[0][0] == "a", fused

# a literal Article-number query ranks the exact Article chunk first --
# dense embeddings are bad at this, BM25 should nail it
chunks = [
    {"chunk_id": "reg:2023:sporting:1:33", "text": "Article 33 (Sporting Regulations, 2023): DRIVING\nDrivers must make every reasonable effort to use the track at all times and may not leave the track without a justifiable reason. 33.3 governs leaving the track."},
    {"chunk_id": "reg:2023:sporting:1:12", "text": "Article 12 (Sporting Regulations, 2023): PENALTIES\nThe stewards may impose a penalty for a breach of these regulations."},
    {"chunk_id": "reg:2023:technical:1:3", "text": "Article 3 (Technical Regulations, 2023): AERODYNAMICS\nBodywork must comply with the dimensions specified."},
]
bm25 = BM25Retriever(chunks)
hits = bm25.search("What does Article 33.3 say about leaving the track?", k=3)
assert hits[0][0] == "reg:2023:sporting:1:33", hits

print("OK — RRF fuses correctly and BM25 ranks the literal Article match first.")
