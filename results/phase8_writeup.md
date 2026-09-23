# Evaluation results

**Restated in Phase 11** after Phase 9 fixed a Superseded Precedent
citation-matching bug and Phase 10 root-caused the reranker regression. The
original Phase 8 numbers are not deleted -- see "What changed since Phase 8"
at the end; the bug and its correction are part of the story, and this
project's own subject matter is superseded precedent.

Eval set: `data/eval_set.json`, **45 questions** (13 seeded contradictions --
9 Divergent Precedent + 4 Superseded Precedent, 7 negative Justified
Distinction cases, 25 ordinary regulation/Decision lookups), all built from
real, verified corpus content (see each question's `notes` field for
provenance; `python -m src.eval.test_eval_set` asserts every `gold_chunk_ids`
entry exists in the corpus).

Full run logs: `results/eval_qwen2.5_3b_full_20260923T140215_*.json` and
`results/eval_qwen2.5_7b_full_20260923T181153_*.json` (summary, per-question
precision detail, full generation output, per-citation faithfulness
judgments, no-retrieval baseline answers). Phase 8's original runs
(`*_20260923T011354_*` and `*_20260923T031322_*`) are kept as-is -- the first
documents a real generation bug (see below), the second is the pre-Phase-9
32-question baseline this restatement supersedes.

## Headline numbers (45 questions, post Phase 9-10)

| Metric | 3B | 7B |
|---|---|---|
| Retrieval precision@8, no rerank | 0.694 (25/36 scored) | identical -- retrieval doesn't depend on the generation model |
| Retrieval precision@8, reranked | 0.694 (25/36 scored) | identical |
| Divergent Precedent recall / precision | 0.667 / 0.75 (6 TP, 3 FN, 5 TN, 2 FP) | identical |
| Superseded Precedent recall / precision | 1.0 / 1.0 (4 TP, up from 1) | identical |
| Questions with >=1 citation | 11/45 | 35/45 |
| Total citations produced | 35 | 100 |
| Citation faithfulness (per-citation, LLM-judge) | 0.971 (1/35 unsupported) | 0.410 (59/100 unsupported) |
| Generation errors | 0 | 1 (Ollama read-timeout on q45, transient -- not a logic error) |

9 of 45 questions were skipped for precision@k because they're deliberately
open-ended or unanswerable by design -- see q08/q09/q24/q25's notes (q24 is
the deliberate-abstention test, load-bearing per the plan's carried-forward
notes; q25 is a genuine multi-source combined lookup that a single pin would
understate).

## Reranking: still a wash, and now explained (Phase 10)

Precision@8 is now **identical with and without reranking** (0.694 both,
25/36) -- but that headline number hides real churn underneath: 8 of 36
scored questions still flip, 4 improved (q04, q13, q27, and the newly added
q40) against the same 4 regressions Phase 8 found (q14, q19, q20, q30).

Phase 10's analysis (`results/rerank_analysis.md`) refutes Phase 8's original
hypothesis that the cross-encoder demotes a correct Article for a
semantically-related but wrong one. The real mechanism: the corpus keeps
every historical Issue of every amended Article as its own chunk (by design,
for observable change history -- CONTEXT.md's "Issue" term), so heavily
amended Articles have large near-duplicate clusters (20 chunks for Article
48, 20 for Article 29, 18 for Article 12) competing for the same rank. The
reranker reshuffles among these near-identical Issues close to arbitrarily --
it never promotes a genuinely wrong Article. With the larger eval set the
net effect is now a wash (4 up, 4 down) rather than a net loss (3 up, 4 down
in Phase 8), which is consistent with "symmetric churn among duplicates," not
a directional bias -- the additional data point (q40) landed on the
"improved" side purely by chance of which season/Issue its gold chunk
happened to be.

## Contradiction recall: real detector limits, not a retrieval bug this time

Divergent Precedent: 6/9 recall (up from Phase 8's framing of "3 misses, all
retrieval-depth"). The 3 misses (q01, q10, q32) are the same retrieval-depth
pattern Phase 8 found -- the retriever's top-8 for that question's phrasing
doesn't surface both halves of the pair needed to form the divergence.

**New finding in Phase 11**: both Divergent Precedent false positives (q05,
q38) share a real, previously-unsurfaced detector limitation. Both
questions' *intended* Decision pair is correctly suppressed (verified
directly against `detect_divergent_precedent`'s output -- q05's Document
66-vs-63 pair carries `evidence: ["occasion_count differs...", "prior_sanction
differs..."]` and is suppressed as designed). The false positive comes from a
*different*, unsuppressed flag among the same 8 retrieved chunks, caused by
`_normalise_outcome` in `src/contradiction/divergent_precedent.py` only
lowercasing and stripping trailing periods -- so "5 second time penalty." and
"5 second time penalty. (5 seconds added to elapsed Race time)." are treated
as *different* outcomes (a real divergence) when they are the same penalty,
just phrased with an added clause. This is a real precision gap in the
outcome-comparison logic, not a metric-authoring mistake, surfaced only now
because the larger eval set's broader Article-33.3/12.2.1 retrieval happens
to pull in these near-duplicate-outcome pairs. Not fixed in this phase --
changing detection logic here would invalidate this run's own numbers; flagged
as a known limitation below and a concrete next step.

Superseded Precedent: 4/4 recall and precision, the real number Phase 9
made possible -- q04 (existing, Article 44) plus three new questions (q33:
Article 27.1, q34: Article 48.1, q35: Article 40.3), each verified by diffing
actual sub-clause text between regulation Issues (not just relying on the
Article-level "text changed" flag, which Phase 8 already found can be a false
positive at sub-clause granularity -- e.g. Article 34.7's actual pit-speed
text is unchanged across all of 2023 despite the Article-level table saying
otherwise). `data/controversies.md` entries 9, 10, 11 (the plan's suggested
Superseded leads) were checked and rejected: entry 9 is a process/enforcement
change with no Article text change (matches Phase 8's finding that Article
33's text never moved), entry 10 isn't a numbered Regulation Article at all,
and entry 11's candidate Decision (58.8, safety car restart) turned out to be
a PDF-parsing duplicate-numbering artifact, not a real content change, on
inspection of the actual before/after text.

## Citation faithfulness: the 3B/7B split, more pronounced at scale

Same direction as Phase 8, more visible with more questions:

- **qwen2.5:3b** answers with a citation on only 11/45 questions (35 total
  citations) but is nearly perfectly faithful when it does (0.971, 1
  unsupported of 35) -- it still prefers an uncited prose answer to an
  unsupported citation.
- **qwen2.5:7b** cites far more often (35/45 questions, 100 total citations)
  but at much lower faithfulness (0.410, 59/100 unsupported) -- more than
  half its citations don't actually support what it claims. This is a wider
  gap than Phase 8's 0.72/0.60 split on the smaller set; the larger,
  denser-with-near-duplicates eval set (more 33.3/12.2.1/Article-48-family
  questions with several near-identical Decisions in context) appears to
  make 7B's cross-chunk conflation failure mode (traced concretely in Phase
  8's q01 case) worse, not better.

Net: bigger model, far more willing to commit to a citation, but
substantially more prone to mixing up which near-duplicate source it's
quoting. Neither failure mode is flattering, and reporting both -- now with a
much larger faithfulness sample (100 vs 80 citations for 7B) -- is more
informative than either number alone.

## A real generation bug found and fixed in Phase 8 (unchanged)

The first full 3B run (`*_20260923T011354_*`, kept for the record) had 21 of
32 generations fail outright, fixed by passing a full JSON Schema as
Ollama's `format` parameter rather than a plain-text instruction (see
`src/generate/generate.py:RESPONSE_SCHEMA`). Unaffected by Phases 9-11; kept
here for continuity. The Phase 11 7B run had 1 transient Ollama read-timeout
(q45, `HTTPConnectionPool ... Read timed out`) -- a network/process issue,
not a repeat of the schema bug; not re-run, consistent with this project's
practice of keeping imperfect runs as the honest record.

## No-retrieval baseline

Unchanged in character from Phase 8: `results/*_baseline.json` holds raw
model answers with no retrieved context, for both models. The domain-specific
gap retrieval closes (specific Decision documents, dates, outcomes that the
base model cannot know) is unchanged by Phases 9-11's fixes, since those
fixes are to the contradiction/reranking layers, not retrieval or generation
itself.

## What changed since Phase 8

- **Phase 9** fixed Superseded Precedent citation matching: Decisions cite
  sub-clause Article IDs (`33.3`) but `article_changes.json` was keyed by
  top-level Article (`33`), so only 1 of 37 distinct cited IDs could match.
  `src/contradiction/article_ids.py::top_level_article` normalises the
  lookup; flags now carry `match_granularity` (`"exact"` vs `"article"`) so
  the precision cost of Article-level matching is visible rather than
  hidden. Corpus-wide flags went from 9 (all one Decision) to 558 across 89
  Decisions.
- **Phase 10** root-caused the reranker regression Phase 8 could report but
  not explain (see above) -- refuted the original hypothesis, found the real
  mechanism (near-duplicate Issue/season chunks), no pipeline code changed.
- **Phase 11** (this restatement): eval set grown from 32 to 45 questions;
  Superseded Precedent went from 1 (propped up by the Phase 9 bug) to 4 real,
  independently-verified questions; q10 and q32 pinned to specific verified
  Decision pairs; q24/q25 given explicit notes on why they stay unpinned;
  both models re-run in full; a new Divergent Precedent outcome-normalisation
  limitation surfaced and documented (not fixed).

## Known limitations (see also CLAUDE.md / PLAN.md)

- **The judge is qwen2.5:3b judging qwen2.5-family output.** Not
  GPT-4-class evaluation; the faithfulness numbers above should be read as
  directional, not precise.
- **The eval set is self-authored** (45 questions as of Phase 11), including
  the negative cases used for contradiction precision.
- **Contradiction ground truth is interpretive** -- "materially similar
  incident" is a judgment call made by one non-steward, encoded as a
  0.75 Fact-embedding-similarity threshold (`src/contradiction/
  divergent_precedent.py:SIMILARITY_THRESHOLD`), not a rule from the FIA.
- **Divergent Precedent's outcome comparison is string-normalisation only**
  (Phase 11 finding, above) -- `_normalise_outcome` doesn't recognise
  "5 second time penalty" and "5 second time penalty (5 seconds added to
  elapsed Race time)" as the same outcome, producing false positives when
  such near-duplicate-outcome pairs happen to be retrieved together. A
  semantic outcome-equivalence check (or normalising away the "(N seconds
  added to elapsed ... time)" boilerplate specifically) is the natural next
  step; not implemented here to avoid changing detection logic mid-eval-run.
- **Superseded Precedent's Article-level match_granularity is a real,
  stated precision cost** (Phase 9): an Article-level text change does not
  prove the cited sub-clause itself changed. 4/4 of the current questions
  happen to be genuine sub-clause changes (manually verified), but the
  corpus-wide 558-flag count includes many Article-level matches that were
  not individually verified this way -- see `results/parse_coverage.json`'s
  `citation_corpus_coverage` for the aggregate normalisable/ISC split.
- **CPU-only inference on 2020 Intel hardware** made both full runs take
  on the order of an hour each; this shaped the eval set size (45, not
  hundreds) as much as any methodological choice.
