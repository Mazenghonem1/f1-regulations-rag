# Phase 8 — Evaluation results

Eval set: `data/eval_set.json`, 32 questions (8 seeded contradictions, 4
negative Justified Distinction cases, 20 ordinary regulation/Decision
lookups), all built from real, verified corpus content (see each question's
`notes` field for provenance).

Full run logs: `results/eval_qwen2.5_3b_full_20260923T031322_*.json` and
`results/eval_qwen2.5_7b_full_20260923T063807_*.json` (summary, per-question
precision detail, full generation output, per-citation faithfulness
judgments, no-retrieval baseline answers). An earlier 3B run
(`eval_qwen2.5_3b_full_20260923T011354_*`) is kept as-is rather than deleted
-- it documents a real bug (below) rather than a clean result.

## Headline numbers

| Metric | 3B | 7B |
|---|---|---|
| Retrieval precision@8, no rerank | 0.654 (17/26 scored) | identical -- retrieval doesn't depend on the generation model |
| Retrieval precision@8, reranked | 0.615 (16/26 scored) | identical |
| Divergent Precedent recall / precision | 0.571 / 0.800 | identical -- detector doesn't depend on the generation model |
| Superseded Precedent recall / precision | 1.0 / 1.0 (1 example) | identical |
| Questions with >=1 citation | 14/32 | 30/32 |
| Total citations produced | 46 | 80 |
| Citation faithfulness (per-citation, LLM-judge) | 0.717 | 0.600 |
| Generation errors | 0 | 0 |

6 of 32 questions were skipped for precision@k because they're deliberately
open-ended (several valid Decision pairs exist for the underlying
controversy -- see `q08`/`q09`/`q10`/`q32`'s notes), so precision@k is
scored over the 26 questions with a single fixed gold chunk set.

## Reranking: a real regression, not a clean win

Reranking flipped 7 of 26 scored questions (27%): 3 improved (q04, q13,
q27), 4 regressed (q14, q19, q20, q30), netting one fewer correct question
overall (17 -> 16). This is worth stating plainly rather than assuming
reranking is free precision -- on this corpus and these regulation-lookup
questions, the cross-encoder sometimes demotes the literal-match chunk that
BM25 had already ranked first, in favour of a semantically related but
wrong Article. The eval harness logs pre- and post-rerank order for every
run (`*_precision_detail.json`), so this is a reproducible, inspectable
result, not an assumption.

## Contradiction recall misses: a retrieval-depth problem, not a detector bug

All 3 Divergent Precedent recall misses (q01, q10, q32) trace to the same
root cause: the retriever's top-8 for that question's phrasing didn't
include *both* of the two Decision chunks needed to form the pair. In q01
specifically, all 8 retrieved chunks were from the same Grand Prix (Austrian
GP 2023) -- the Qatar GP decision needed to complete the real divergence
never surfaced. The detector itself is correctly implemented and verified
against hand-built fixtures (`src/contradiction/test_contradiction.py`) and
real corpus pairs (Phase 6) -- recall here is bottlenecked by retrieval,
not detection logic. This is exactly the kind of result the "before/after
reranking" and precision@k numbers above are meant to make legible.

## Citation faithfulness: 3B is falsely silent, 7B is falsely confident

The two models fail in opposite, both-real directions:

- **qwen2.5:3b** answered 18 of 32 questions with zero citations at all,
  even when directly instructed and even under JSON-schema-constrained
  decoding (see "A real generation bug" below) -- it would rather write an
  unsupported prose answer than commit to a specific `doc_id`. Spot-checked
  (q29): the underlying cause here was actually a retrieval miss (none of
  the 8 retrieved chunks were the Article the question needed), and the
  model correctly declined to fabricate a citation to the wrong chunk
  rather than a pure citation-compliance failure -- a defensible response,
  just not a useful one for the faithfulness metric.
- **qwen2.5:7b** cited far more often (30/32 questions, 80 total citations)
  but with a lower per-citation faithfulness rate (0.60 vs 3B's 0.72).
  Traced one concrete failure (q01): 7B correctly named
  `dec:2023:Austrian Grand Prix:66` as a citation, but then quoted
  `dec:2023:Austrian Grand Prix:63`'s actual Reason text ("four occasions
  ... black and white flag") while attributing it to 66 -- a real
  cross-chunk conflation when several near-identical Decisions (all "left
  the track without justifiable reason" under Article 33.3) sit together
  in context, not a judge artifact. Verified against the ground truth
  established in Phase 6: Document 66's real Reason text is "seven (7)
  occasions ... after having received a 5 second time penalty on the
  fourth (4th) occasion."

Net: bigger model, more willing to commit to a citation, but more prone to
mixing up which near-duplicate source it's quoting when several similar
Decisions are retrieved together. Neither failure mode is flattering, and
reporting both is more informative than either faithfulness number alone --
this is the 3B/7B delta PLAN.md asks for.

## A real generation bug found and fixed mid-phase

The first full 3B run (`*_20260923T011354_*`, kept for the record) had 21
of 32 generations fail outright. Two distinct failures, found and fixed in
sequence:

1. A plain-text "respond with ONLY a JSON object" instruction was ignored
   on longer, more analytical questions -- the model answered in prose
   instead, deterministically (the retry-once logic from Phase 7 can't fix
   a failure that repeats identically on retry).
2. Passing Ollama's `format: "json"` fixed the *syntax* but not the
   *shape* -- the model produced valid JSON with an invented schema
   (`{"answer": ..., "reasoning": ...}`) instead of the required
   `{answer, citations, contradictions_flagged}`.

Fix: pass a full JSON Schema as Ollama's `format` parameter
(`src/generate/generate.py:RESPONSE_SCHEMA`), which grammar-constrains the
required keys at decode time rather than relying on the model reading and
following a text instruction. The re-run after this fix had 0 generation
errors on both models. `minItems` on the `citations` array was
deliberately *not* added -- forcing a non-empty array risks the model
fabricating a citation just to satisfy the schema, which would be a worse
outcome (an unfaithful citation) than an honest empty list, and the
faithfulness metric above is specifically designed to catch and penalise
fabrication rather than have the schema paper over it.

## No-retrieval baseline

`results/*_baseline.json` holds the raw model answers with no retrieved
context at all, for both models. Spot check: on the Divergent Precedent
questions (q01-q03, q08-q10, q32), the baseline has no way to know specific
Decision documents, dates, or outcomes exist, and either declines to answer
specifics or fabricates plausible-sounding but unverifiable claims about
"the 2023 season" -- exactly the domain-specific gap retrieval is meant to
close. A full per-question baseline-vs-grounded comparison is left as
manual review material in the logged JSON rather than scored automatically,
since scoring "is this fabricated" without ground truth is itself a
judgment call the local LLM-judge is not more equipped to make than a
human reader here.

## Known limitations (see also CLAUDE.md / PLAN.md)

- **The judge is qwen2.5:3b judging qwen2.5-family output.** Not
  GPT-4-class evaluation; the faithfulness numbers above should be read as
  directional, not precise.
- **The eval set is small (32 questions) and self-authored,** including the
  negative cases used for contradiction precision.
- **Contradiction ground truth is interpretive** -- "materially similar
  incident" is a judgment call made by one non-steward, encoded as a
  0.75 Fact-embedding-similarity threshold (`src/contradiction/
  divergent_precedent.py:SIMILARITY_THRESHOLD`), not a rule from the FIA.
- **CPU-only inference on 2020 Intel hardware** made both full runs take
  on the order of an hour each; this shaped the eval set size (32, not
  hundreds) as much as any methodological choice.
