# Evaluation results

**Restated a second time** after two targeted fixes to Divergent Precedent:
an outcome-normalisation bug (false positives from boilerplate phrasing
differences) and a widened retrieval depth for the contradiction-check-only
retrieval call (recall misses from too-shallow candidate pools). Both are
small, scoped changes -- see "What changed in this restatement" below. Prior
restatements are not deleted; each documents a real, found issue.

Eval set: `data/eval_set.json`, **45 questions** (13 seeded contradictions --
9 Divergent Precedent + 4 Superseded Precedent, 7 negative Justified
Distinction cases, 25 ordinary regulation/Decision lookups), all built from
real, verified corpus content (see each question's `notes` field for
provenance; `python -m src.eval.test_eval_set` asserts every `gold_chunk_ids`
entry exists in the corpus).

Full run logs: `results/eval_qwen2.5_3b_full_20260923T215008_*.json` and
`results/eval_qwen2.5_7b_full_20260924T015845_*.json`. Earlier runs
(`*_20260923T140215_*`, `*_20260923T181153_*`, and Phase 8's originals) are
kept as-is -- each documents a real state of the system at the time.

## Headline numbers (45 questions, post outcome-normalisation and retrieval-depth fixes)

| Metric | 3B | 7B |
|---|---|---|
| Retrieval precision@8, no rerank | 0.694 (25/36 scored) | identical -- unaffected by either fix (see below) |
| Retrieval precision@8, reranked | 0.694 (25/36 scored) | identical |
| Divergent Precedent recall / precision | **0.889 / 0.667** (8 TP, 1 FN, 3 TN, 4 FP) | identical |
| Superseded Precedent recall / precision | 1.0 / 1.0 (4 TP) | identical |
| Questions with >=1 citation | 28/45 | 39/45 |
| Total citations produced | 28 | 114 |
| Citation faithfulness (per-citation, LLM-judge) | 0.893 (3/28 unsupported) | 0.263 (84/114 unsupported) |
| Generation errors | 0 | 1 (Ollama read-timeout on q06, transient -- not a logic error) |

9 of 45 questions were skipped for precision@k because they're deliberately
open-ended or unanswerable by design -- see q08/q09/q24/q25's notes (q24 is
the deliberate-abstention test, load-bearing per the plan's carried-forward
notes; q25 is a genuine multi-source combined lookup that a single pin would
understate).

## Divergent Precedent: recall up, precision down -- a real, understood tradeoff

Two fixes, deliberately scoped narrow to avoid touching precision@8, what the
LLM sees during generation, or the app:

1. **Outcome-normalisation fix** (`src/contradiction/divergent_precedent.py`):
   `_normalise_outcome` now strips the "(N seconds added to elapsed Race/Sprint
   time)" boilerplate clause before comparing two Decisions' Outcomes, in
   addition to the existing period-stripping. Verified against the exact
   false positives this was found from (q05, q38 in the prior restatement):
   "5 second time penalty." and "5 second time penalty. (5 seconds added to
   elapsed Race time)." now normalise identically. Penalty-points text is
   deliberately *not* stripped -- "10 second time penalty" and "10 second
   time penalty + 2 penalty points" remain different outcomes, since they
   are.
2. **Retrieval-depth fix** (`src/eval/contradiction_metrics.py`): the
   contradiction-check retrieval call now asks for the top 16 candidates
   instead of 8 (`CONTRADICTION_RETRIEVAL_TOP_N`). A Divergent Precedent pair
   needs *both* Decisions retrieved to be detectable at all -- q01's top-8
   was entirely from one Grand Prix, missing the Decision needed to complete
   the pair. This call only feeds the contradiction check, never generation
   or precision@k, so it doesn't redefine "precision@8" or change what an
   LLM sees.

Result: recall went from 6/9 (0.667) to **8/9 (0.889)** -- q01 and q32 (both
previously retrieval-depth misses) are now correctly flagged. q10 remains a
miss even at top_n=32 (checked): its gold Decisions simply don't rank highly
for that question's phrasing, a genuine query-relevance gap rather than a
depth problem, and not chased further here.

Precision, however, **dropped from 5/7 (0.75) to 6/9 (0.667)** -- 4 FP now
(q05, q07, q38, q40), up from 2. The outcome-normalisation fix worked for its
target case, but widening retrieval to 16 candidates surfaces *more*
candidate pairs overall, including real, independent Divergent Precedent
flags for the same Article that a negative question's own pair doesn't
involve (verified: q05's new FP is Document 75 vs a 2024 Austrian GP
Decision, an entirely different pair from the Document 66-vs-63 pair q05 is
actually about; q40's new FPs are three genuinely different-fine-amount pairs
among Article 34.7 Decisions). This exposes a **pre-existing metric-
granularity issue**, not a regression introduced by either fix:
`_flagged_for_article` in `src/eval/contradiction_metrics.py` checks "is
there *any* unsuppressed flag for this Article among retrieved chunks",
which is coarser than "is the specific pair this question is about flagged."
Widening retrieval makes that gap more visible because more candidates means
more chances to hit an unrelated same-Article pair. Not fixed here --
narrowing `_flagged_for_article` to check the question's own
`gold_chunk_ids` pair specifically is the natural next step, and a separate,
larger change than either of this restatement's two fixes.

Net honest read: the detector's *underlying* behaviour (which pairs it
flags and suppresses) didn't get worse -- verified by hand that every new FP
is a real, independently-correct unsuppressed flag for a genuine pair, not a
bug. What changed is that the eval's per-Article scoring is a blunter
instrument than the detector itself, and giving retrieval more room to work
exposed that bluntness. Recall improving from a real fix while precision
drops from an exposed measurement gap is a legitimate, reportable outcome --
not a wash to explain away.

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

## Superseded Precedent: still 4/4

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

## Citation faithfulness: same 3B/7B split, notable run-to-run variance

Neither fix in this restatement touches `src/generate/` or `run_eval.py`'s
`run_generation` (which still retrieves at `top_n=8`, unaffected by the
contradiction-metrics-only depth change) -- so the faithfulness numbers
moving is Ollama sampling variance (unseeded), not a consequence of either
fix. Reported honestly rather than re-run until it looks stable:

- **qwen2.5:3b**: cited on 28/45 questions this run (vs 11/45 previously),
  faithfulness 0.893 (vs 0.971) -- still clearly the more conservative,
  more faithful model, but noticeably less silent than before.
- **qwen2.5:7b**: cited on 39/45 questions (114 total citations, vs 100
  previously), faithfulness **0.263** (vs 0.410) -- the worst faithfulness
  score seen on this eval set so far, more than 80% of its citations
  unsupported this run.

The direction is consistent across every run of this eval (3B: fewer
citations, higher faithfulness; 7B: more citations, lower faithfulness), but
the exact numbers swing meaningfully run to run -- a reader comparing two
numbers from different runs should treat the *direction* as the finding, not
either specific percentage. This variance is itself worth stating as a
limitation of running the 45-question eval once per change rather than
averaging over several runs (see Known Limitations).

## A real generation bug found and fixed in Phase 8 (unchanged)

The first full 3B run (`*_20260923T011354_*`, kept for the record) had 21 of
32 generations fail outright, fixed by passing a full JSON Schema as
Ollama's `format` parameter rather than a plain-text instruction (see
`src/generate/generate.py:RESPONSE_SCHEMA`). Unaffected by any later
restatement; kept here for continuity. Both restatements' 7B runs have had
exactly 1 transient Ollama read-timeout each (different question each time)
-- a network/process issue under long CPU-bound runs, not a repeat of the
schema bug; not re-run, consistent with this project's practice of keeping
imperfect runs as the honest record.

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
- **Phase 11** (first restatement): eval set grown from 32 to 45 questions;
  Superseded Precedent went from 1 (propped up by the Phase 9 bug) to 4 real,
  independently-verified questions; q10 and q32 pinned to specific verified
  Decision pairs; q24/q25 given explicit notes on why they stay unpinned;
  both models re-run in full; a new Divergent Precedent outcome-normalisation
  limitation surfaced and documented (not fixed).
- **This restatement** implemented the two fixes Phase 11 documented and
  deferred: `_normalise_outcome` now strips the "(N seconds added to
  elapsed... time)" boilerplate clause (fixes q05/q38's specific false
  positives), and `src/eval/contradiction_metrics.py` widens its internal
  retrieval to top_n=16 (fixes q01/q32's retrieval-depth recall misses).
  Both were scoped narrow deliberately -- neither touches precision@8,
  generation context, or the app. Net effect: Divergent Precedent recall
  0.667 -> 0.889, precision 0.75 -> 0.667 (a real, understood tradeoff via a
  pre-existing per-Article metric-granularity gap the wider retrieval made
  visible, not a new bug -- see above).

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
- **Divergent Precedent's outcome comparison is still string-normalisation,
  not semantic** -- this restatement fixed the one specific boilerplate
  pattern found (the "(N seconds added to elapsed... time)" clause), but any
  other phrasing variant of the same real outcome (different word order,
  a synonym, a typo) would still be treated as a divergence. A semantic
  outcome-equivalence check (e.g. embedding similarity on the outcome text,
  the same technique already used for Fact-text similarity) is the natural
  further step.
- **`_flagged_for_article`'s per-Article granularity is a real metric gap**,
  surfaced by this restatement's retrieval-depth fix: it checks "is there
  any unsuppressed flag for this Article", not "is the specific pair this
  question names flagged." Widening retrieval exposed this because more
  candidates means more chances to hit an unrelated same-Article pair.
  Narrowing the check to the question's own `gold_chunk_ids` is the natural
  fix, deliberately not done in this restatement to keep the two fixes here
  independently attributable.
- **Faithfulness numbers vary meaningfully run to run** (this restatement's
  finding, above) -- Ollama sampling is unseeded, and this eval runs each
  model once per restatement rather than averaging several runs. The
  direction (3B conservative/faithful, 7B chatty/unfaithful) is consistent;
  the exact percentages are not precise enough to compare two runs to the
  second decimal place.
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
