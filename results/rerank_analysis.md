# Reranker regression analysis

Evidence: `results/rerank_analysis_detail.json`, produced by
`python -m src.eval.analyse_rerank` re-running retrieval for the 7 flipped
questions from `results/eval_qwen2.5_3b_full_20260923T031322_precision_detail.json`
(Precision@8: 0.654 → 0.615 with reranking, 17/26 → 16/26). Retrieval is
deterministic given the fixed corpus, so this reproduces exactly what
`log_query` would have written had `precision_at_k` called it.

## What was hypothesized

The write-up guessed the cross-encoder demotes a literal Article-number
match that BM25 ranked correctly, in favour of a semantically-related but
*wrong* Article.

## What the evidence shows

That hypothesis is **refuted**. In all 7 flipped questions — the 4
regressions (q14, q19, q20, q30) and, on inspection, the 3 improvements too
(q13 clearly, q04/q27 are Decision-side and different) — the reranker never
promotes a wrong *Article*. The chunks that outrank the gold post-rerank cite
the **same Article number**, just a different season/Issue:

| id | direction | gold | pre-rank | post-rank | displaced by |
|---|---|---|---|---|---|
| q14 | regressed | `reg:2023:sporting:1:48` | 2 | 11 | `reg:2024:sporting:2:48`, `reg:2024:sporting:4:48` |
| q19 | regressed | `reg:2024:sporting:4:40` | 4 | 9 | `reg:2024:sporting:7:40`, `reg:2024:sporting:6:40`, `reg:2025:sporting:3:40` |
| q20 | regressed | `reg:2023:technical:1:12` | 3 | 12 | `reg:2024:technical:4:12`, `reg:2024:technical:6:12`, `reg:2024:technical:5:12` |
| q30 | regressed | `reg:2023:sporting:1:29` | 6 | 16 | `reg:2023:sporting:7:29`, `reg:2023:sporting:8:29`, `reg:2024:sporting:1:29` |
| q13 | improved | `reg:2023:sporting:1:28` | 11 | 6 | (same pattern, reversed direction) |

## The real mechanism: near-duplicate Issue/season chunks

The corpus keeps every historical Issue of every Article as its own chunk
(by design — CONTEXT.md's "Issue" term, change history needs it observable).
For a heavily-amended Article this produces a large cluster of
near-identical text competing for the same rank:

- Article 48 (sporting): **20** chunks across 2023–2025 seasons/Issues.
- Article 29 (sporting): **20** chunks.
- Article 12 (technical): **18** chunks.
- Article 40 (sporting): **9** chunks.

Diffing the gold chunk against its top displacer (q14: `reg:2023:sporting:1:48`
vs `reg:2024:sporting:2:48`) shows near-identical body text — same clause
numbering, same wording, differing only in `pdftotext -layout` line-wrap
whitespace and the season line. There is no real semantic difference for the
cross-encoder to key off of when the question doesn't name a season
(all 7 flipped questions are Article-only queries — "How many power units...",
"What construction requirements...", with no year mentioned).

Given near-duplicate candidates, the cross-encoder's fine-grained scoring
reorders among them close to arbitrarily relative to BM25's fused rank. It
demotes the gold Issue in 4 cases and promotes it in at least 1 (q13) — a
symmetric churn, not a directional bias toward wrong content. Both pre- and
post-rerank rankings put *a* correct Article 48 chunk in the top few; only
the eval's single-gold-Issue scoring (`gold_chunk_ids` pins one specific
Issue) counts the swap as a miss.

## Question-type split

q14/q19/q20/q30 are all `ordinary_lookup`, q04/q13/q27 span a
`seeded_contradiction` (q04) and lookups (q13, q27). That split does not
explain the direction of the flip — q13 is `ordinary_lookup` too, and
improved via the identical same-Article-different-Issue mechanism as the
four regressions. Question type is not the driver; **whether an Article has
many near-duplicate historical Issues in the corpus is.**

## Recommendation (not implemented at the time of this analysis)

The precision cost here is largely an artifact of scoring against one
gold Issue while the corpus intentionally retains all Issues. Two options,
neither implemented at the time of this analysis:

1. **Eval-side**: score precision@k as a hit if *any* Issue of the gold
   Article appears in top-k, not just the pinned Issue — this measures
   "found the right Article" separately from "found the current Issue."
   (Later added -- see `src/eval/precision_at_k.py`'s `article_level` metric.)
2. **Retrieval-side**: query-time season/recency biasing, or collapsing
   near-duplicate Issues at rerank time — out of scope here; changing
   retrieval would invalidate other eval numbers already reported elsewhere.

No pipeline code was changed as part of this analysis.
