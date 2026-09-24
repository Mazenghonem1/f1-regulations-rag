# Evaluation results

**Restated a third time.** The second restatement fixed two real bugs
(outcome-normalisation, retrieval depth) but exposed a third, pre-existing
metric-granularity gap that cost precision. This restatement fixes that gap
directly, plus two more real extraction bugs found while investigating the
one remaining recall miss. Net result: **Divergent Precedent recall 0.889,
precision 1.0** -- both up, no tradeoff. Prior restatements are not deleted;
each documents a real, found issue, and the sequence itself (bug found ->
fix -> fix exposes next bug -> fix) is part of the story.

Eval set: `data/eval_set.json`, **45 questions** (13 seeded contradictions --
9 Divergent Precedent + 4 Superseded Precedent, 7 negative Justified
Distinction cases, 25 ordinary regulation/Decision lookups), all built from
real, verified corpus content (see each question's `notes` field for
provenance; `python -m src.eval.test_eval_set` asserts every `gold_chunk_ids`
entry exists in the corpus).

Full run logs: `results/eval_qwen2.5_3b_full_20260924T110038_*.json` and
`results/eval_qwen2.5_7b_full_20260924T142653_*.json`. Earlier runs are kept
as-is -- each documents a real state of the system at the time.

## Headline numbers (45 questions, current state)

| Metric | 3B | 7B |
|---|---|---|
| Retrieval precision@8, no rerank | 0.694 (25/36 scored) | identical -- unaffected by any contradiction-layer fix |
| Retrieval precision@8, reranked | 0.694 (25/36 scored) | identical |
| Divergent Precedent recall / precision | **0.889 / 1.0** (8 TP, 1 FN, 7 TN, 0 FP) | identical |
| Superseded Precedent recall / precision | 1.0 / 1.0 (4 TP) | identical |
| Questions with >=1 citation | 11/45 (42 total citations) | 38/45 (91 total citations) |
| Citation faithfulness (per-citation, LLM-judge) | 0.905 (4/42 unsupported) | 0.462 (49/91 unsupported) |
| Generation errors | 0 | 1 (Ollama read-timeout on q09, transient -- not a logic error) |

9 of 45 questions were skipped for precision@k because they're deliberately
open-ended or unanswerable by design -- see q08/q09/q24/q25's notes (q24 is
the deliberate-abstention test, load-bearing per the plan's carried-forward
notes; q25 is a genuine multi-source combined lookup that a single pin would
understate).

## Divergent Precedent: three real bugs, found and fixed in sequence

The second restatement (see "What changed" below) fixed two bugs but landed
at recall 0.889 / precision 0.667 -- a real tradeoff traced to a third,
separate issue: `_flagged_for_article` in `src/eval/contradiction_metrics.py`
only checked "is there any unsuppressed flag for this Article", not "is the
specific pair this question names flagged." This restatement fixes that
directly, and in verifying the fix, found two more real bugs in the same
investigation:

1. **Metric-granularity fix**: added `_flagged_for_pair`, which checks the
   question's own `gold_chunk_ids` (exactly 2 ids for `divergent_precedent`,
   1 for `superseded_precedent`) against the specific flag, falling back to
   the coarser per-Article check only for q08/q09 (deliberately open-ended,
   no fixed pair to check against). New test:
   `src/eval/test_contradiction_metrics.py`.
2. **Investigating the one remaining false negative (q01) surfaced a real
   extraction bug** in `src/contradiction/mitigating.py`: 2023 Qatar GP
   Document 81's Reason text reads "after having received 5 second time
   penalties on the fourth (4th) and fifth (5th) occasions" -- a compound,
   plural form. The original `OCCASION_COUNT_RE` only matched the singular
   "on the Nth occasion" form and returned `None` on this real Decision text,
   and `PRIOR_PENALTY_RE` required an article ("a"/"the ... penalty") that
   the plural "penalties" phrasing omits. Both returned no evidence for
   Document 81, so `is_justified_distinction` wrongly reported *no*
   difference from Document 66's genuinely different escalation pattern,
   incorrectly suppressing a real divergence the eval set's own notes
   (verified in Phase 6) call out. Both regexes fixed to handle the compound
   form; the first ordinal is the escalation point that matters, same as the
   singular form.

Verified end-to-end, not just at the regex level: a new test in
`test_contradiction.py` reconstructs Document 66 and 81's actual Fact/Reason
text and asserts the real pair is now correctly flagged and unsuppressed.

Result: recall **0.889** (8/9 -- q01 and q32 both now correctly flagged; q10
remains a miss, checked up to retrieval top_n=32, and is a genuine
query-relevance gap, not a depth or detection-logic problem). Precision
**1.0** (0/9 false positives, down from 4) -- every prior false positive
(q05, q07, q38, q40) is now correctly a true negative, because
`_flagged_for_pair` no longer credits an unrelated same-Article flag for a
negative question it isn't about.

## A semantic outcome-matching approach was tried and measured, then rejected

Before committing to the metric-granularity fix, semantic (embedding)
similarity was tested as a more general replacement for
`_normalise_outcome`'s string-based boilerplate stripping -- the natural
next step the prior restatement's Known Limitations flagged. Measured
directly against real corpus Outcome text before writing any code:
"5 second time penalty" vs "10 second time penalty" (genuinely different
penalties) scores **0.917** cosine similarity -- *higher* than "5 second
time penalty" vs its own true boilerplate-only variant, "5 second time
penalty. (5 seconds added to elapsed Race time)." (0.895). Broader sampling
across all 77 distinct Outcome strings in the corpus confirmed this
isn't a fluke: several genuinely-different Outcome pairs (near-duplicate
"No further action" Reason paragraphs differing only in speed thresholds or
session) score up to **1.000**, higher than the lowest true-duplicate pair
(0.885). The two populations overlap completely -- there is no similarity
threshold that separates "same penalty, reworded" from "different penalty,
same template" on this corpus, because the Outcome field's short, templated
phrasing differs by only a few tokens in both cases. Embedding similarity
would risk suppressing genuine divergences (a worse failure mode than the
original bug, since it hits the headline recall metric directly), so it was
not implemented. The narrow string-based fix from the prior restatement
remains the actual solution for the one real pattern found in this corpus.

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

None of this restatement's fixes touch `src/generate/` or `run_eval.py`'s
`run_generation` (which still retrieves at `top_n=8`, unaffected by the
contradiction-metrics-only depth change) -- so the faithfulness numbers
moving between runs is Ollama sampling variance (unseeded), not a
consequence of any fix here. Reported honestly rather than re-run until it
looks stable:

- **qwen2.5:3b**: cited on 11/45 questions (42 total citations), faithfulness
  **0.905** (4/42 unsupported) -- consistent with every prior run's finding
  that 3B is the more conservative, more faithful model.
- **qwen2.5:7b**: cited on 38/45 questions (91 total citations), faithfulness
  **0.462** (49/91 unsupported) -- roughly half its citations unsupported,
  in line with every prior run's finding for 7B (0.410, 0.263 in earlier
  restatements).

The direction is consistent across every run of this eval (3B: fewer
citations, higher faithfulness; 7B: more citations, lower faithfulness), but
the exact numbers swing meaningfully run to run (7B's faithfulness has
ranged 0.263-0.462 across the last three runs alone) -- a reader comparing
two numbers from different runs should treat the *direction* as the finding,
not either specific percentage. This variance is itself worth stating as a
limitation of running the 45-question eval once per change rather than
averaging over several runs (see Known Limitations).

## A real generation bug found and fixed in Phase 8 (unchanged)

The first full 3B run (`*_20260923T011354_*`, kept for the record) had 21 of
32 generations fail outright, fixed by passing a full JSON Schema as
Ollama's `format` parameter rather than a plain-text instruction (see
`src/generate/generate.py:RESPONSE_SCHEMA`). Unaffected by any later
restatement; kept here for continuity. Every 7B full run since has had
exactly 1 transient Ollama read-timeout (a different question each time --
q45, q06, now q09) -- a network/process issue under long CPU-bound runs, not
a repeat of the schema bug; not re-run, consistent with this project's
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
- **Phase 11** (first restatement): eval set grown from 32 to 45 questions;
  Superseded Precedent went from 1 (propped up by the Phase 9 bug) to 4 real,
  independently-verified questions; q10 and q32 pinned to specific verified
  Decision pairs; q24/q25 given explicit notes on why they stay unpinned;
  both models re-run in full; a new Divergent Precedent outcome-normalisation
  limitation surfaced and documented (not fixed).
- **Second restatement** implemented the two fixes the first restatement
  documented and deferred: `_normalise_outcome` now strips the "(N seconds
  added to elapsed... time)" boilerplate clause (fixed q05/q38's specific
  false positives), and `src/eval/contradiction_metrics.py` widened its
  internal retrieval to top_n=16 (fixed q01/q32's retrieval-depth recall
  misses). Both were scoped narrow deliberately. Net effect at the time:
  Divergent Precedent recall 0.667 -> 0.889, precision 0.75 -> 0.667 (a
  real, understood tradeoff via a pre-existing per-Article metric-
  granularity gap the wider retrieval made visible, not a new bug).
- **This restatement** fixed that metric-granularity gap directly
  (`_flagged_for_pair`, scoring the question's own `gold_chunk_ids` pair
  instead of any same-Article flag), and in verifying the fix, found and
  fixed two more real regex bugs in `src/contradiction/mitigating.py`
  (`OCCASION_COUNT_RE` and `PRIOR_PENALTY_RE` both missed a real compound
  "Nth and Mth occasions" / plural "penalties" phrasing in 2023 Qatar GP
  Document 81's actual text, wrongly suppressing q01's genuine divergence).
  A semantic outcome-matching approach was also tried and measured before
  being rejected with evidence (see above). Net effect: Divergent Precedent
  recall 0.889 (unchanged), precision 0.667 -> **1.0** -- the tradeoff from
  the second restatement is now fully resolved.

## Known limitations (see also PROJECT_BRIEF.md / PLAN.md)

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
  not semantic, and this is deliberate** -- semantic (embedding) matching
  was tried and measured (see above): on this corpus, genuinely different
  Outcomes can score *higher* similarity than true boilerplate-only
  duplicates (up to 1.000 vs as low as 0.885), because the Outcome field's
  short, templated phrasing differs by only a few tokens in both cases. No
  threshold separates the two populations. `_normalise_outcome` handles the
  one specific boilerplate pattern actually found in this corpus; any other
  phrasing variant of the same real outcome would still read as a
  divergence, and fixing that would need a different technique than either
  string rules or embedding similarity (e.g. extracting a structured penalty
  amount/type rather than comparing free text).
- **`_flagged_for_pair`'s exact-match relies on the eval set's own
  `gold_chunk_ids` shape** (exactly 2 ids for `divergent_precedent`, 1 for
  `superseded_precedent`) -- any future question added without that exact
  shape silently falls back to the coarser per-Article check
  (`_flagged_for_article`), which reintroduces the metric-granularity gap
  this restatement fixed. `src/eval/test_contradiction_metrics.py` checks
  the function's logic but not that every future question is authored with
  the right shape.
- **`mitigating.py`'s escalation-language regexes are still pattern-matched
  against known phrasings**, not a general parser -- this restatement fixed
  the two real variants found in this 187-Decision corpus (compound "Nth and
  Mth occasions", plural "penalties" without an article), but a differently-
  worded escalation clause in Decisions outside this corpus could still slip
  through unrecognised, silently suppressing a real divergence the same way
  q01 was before this fix.
- **Faithfulness numbers vary meaningfully run to run** (documented across
  three restatements now, 7B's faithfulness has ranged 0.263-0.462) --
  Ollama sampling is unseeded, and this eval runs each model once per
  restatement rather than averaging several runs. The direction (3B
  conservative/faithful, 7B chatty/unfaithful) is consistent; the exact
  percentages are not precise enough to compare two runs to the second
  decimal place.
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
