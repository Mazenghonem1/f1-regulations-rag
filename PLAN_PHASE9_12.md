# Implementation Plan — Phases 9–12 (post-PLAN.md)

Planned and executed one phase per session.
Continues `PLAN.md`, which ended at Phase 8. Same ground rules apply.

## Ground rules for the executing agent

- **Read `CONTEXT.md` first.** Use its terms exactly. "Contradiction" is an
  umbrella, never a detector name.
- **Every phase ends with a runnable check** — an `assert`-based `__main__`
  self-check or one small `test_*.py`. No test frameworks, no fixtures.
- **Stop at a phase boundary** and report. Do not roll into the next phase.
- **No paid APIs anywhere.** Local Ollama only (`qwen2.5:3b` / `qwen2.5:7b`,
  both pulled and verified working as of 2026-09-23).
- **Commit at each phase end**, following the existing commit-message style:
  state what was built, and state any real bug found and fixed along the way.
- **Verify claims against the corpus before writing them down.** Phase 8
  caught an invented eval example this way; the same discipline applies here.
- Re-running the full eval costs ~1 hour per model on this hardware. Budget
  for it; run it in the background and do other work while waiting.

## Phase ordering rationale

Phase 9 is first because it fixes a **correctness bug that invalidates a
metric already reported in `results/phase8_writeup.md`**. Phases 10 and 11
both depend on 9's outcome (the eval set and the write-up both have to be
restated afterwards). Phase 12 is last because a README should describe the
final state, not a state being actively rewritten.

| Phase | What | Depends on |
|---|---|---|
| 9 | Sub-clause citation matching (**correctness fix**) | — |
| 10 | Reranker regression root-cause | — (can run before 9, but report after) |
| 11 | Eval set expansion + re-run + write-up restatement | 9, 10 |
| 12 | README / portfolio write-up | 9, 10, 11 |

---

## Phase 9 — Sub-clause citation matching (correctness fix)

**Goal:** make Superseded Precedent actually work. It currently almost never
can.

### The bug

Decisions cite **sub-clause** Article IDs (`33.3`, `34.7`, `40.9`).
`data/processed/article_changes.json` is keyed by **top-level** Article IDs
(`33`, `34`, `40`), because Phase 3's chunker deliberately splits regulations
at top-level Article granularity (see `src/chunk/regulations.py`'s docstring
— that was a correct decision for retrieval, it just never got reconciled
with citation matching).

Verified on the current corpus:

- 37 distinct cited Article IDs across all Decisions.
- **1** of them (`44`) can match a change-table key. It only matches because
  that one Decision happened to cite a bare Article number.
- 29 are dotted sub-clauses that **structurally cannot** match.
- 7 are `Appendix L Chapter IV Article 2(x)` citations — International
  Sporting Code, which is **not in the corpus at all** (`docs/RECON.md`
  covers only Sporting/Technical Regulations).

Consequence: `detect_superseded_precedent` produces 9 flags corpus-wide, all
from that single Decision. The `1.0 / 1.0` Superseded Precedent recall and
precision in `results/phase8_writeup.md` is measuring **one lucky case**, not
a working detector. That number must not be left standing as-is.

### Work

1. **Normalise citation → Article for change lookup.** A Decision citing
   `33.3` should match change history for Article `33`. Add a small helper
   (suggested: `src/contradiction/article_ids.py`) exposing something like
   `top_level_article(cited_id) -> str | None`:
   - `"33.3"` → `"33"`; `"12.2.1"` → `"12"`; `"C3.14.4"` → `"C3"` (the 2026+
     section-prefixed form — `CONTEXT.md` defines it; no 2026 data is in the
     corpus today, but the parser already handles the notation, so don't
     regress it).
   - `"Appendix L Chapter IV Article 2(d)"` → `None`. These are ISC
     citations with no corpus counterpart. Returning `None` (not a guess) is
     the point — see step 3.
2. **Use it in `src/contradiction/superseded_precedent.py`.** Look up change
   history by normalised top-level Article, but **keep reporting the Decision's
   originally-cited sub-clause ID in the flag** — a user needs to see `33.3`,
   which is what the Decision actually says, not `33`.
3. **Record the precision cost honestly, in the flag itself.** An Article-level
   change does **not** prove the cited *sub-clause* changed — Article 33 can be
   amended at 33.1 while 33.3 is untouched. This makes the fixed detector
   higher-recall but lower-precision, and that tradeoff must be visible rather
   than hidden:
   - Add a field to each emitted flag (suggested: `match_granularity`) set to
     `"article"` when the match came via sub-clause→Article normalisation, vs
     `"exact"` when the Decision cited a bare Article that matched directly.
   - **Optional, only if the diff proves tractable:** narrow this by checking
     whether the specific sub-clause line changed between the two Issues. The
     Article bodies are already stored (`data/processed/regulation_articles.json`
     has full `body` text and a `sub_articles` list per chunk), so a
     sub-clause-level diff is *possible* — but do not let this block the phase.
     If it works, set `match_granularity: "sub_clause"` and report it. If it's
     messy, ship step 3's flag field and say so. `PLAN.md`'s Phase 4 already
     set this precedent ("fall back to hand-coding ... only if the diff proves
     intractable").
4. **Count ISC citations as a known corpus gap.** 7 of 37 cited IDs are
   Appendix L. Don't silently drop them — emit a count (to `results/`, or into
   the existing coverage report) so the write-up can state "N% of Decision
   citations point outside the corpus" as a measured fact.

**Check:** extend `src/contradiction/test_contradiction.py`:
- `top_level_article("33.3") == "33"`, `("12.2.1") == "12"`,
  `("C3.14.4") == "C3"`, `("Appendix L Chapter IV Article 2(d)") is None`.
- A Decision citing `33.3`, dated before a recorded change to Article `33`,
  is flagged superseded — **and the flag still reports `33.3`**, not `33`.
- A Decision citing an Appendix L Article is **not** flagged (no corpus
  counterpart to compare against), and does not raise.

**Done when:** the detector fires on sub-clause citations; the flag carries
both the original citation and the match granularity; the check passes.

> Do not re-run the full eval in this phase. Phase 11 does that once, after
> Phase 10's findings are also in. Do note the new corpus-wide Superseded
> flag count in the commit message — the jump from 9 is the result.

---

## Phase 10 — Reranker regression root-cause

**Goal:** explain *why* reranking is a net negative here. Currently
`results/phase8_writeup.md` reports the regression honestly but can't explain
it, which is a weaker result than it needs to be.

### What's known

From `results/eval_qwen2.5_3b_full_20260923T031322_precision_detail.json`:

- Precision@8: **0.654 → 0.615** with reranking (17/26 → 16/26).
- 7 of 26 questions flip. Improvements: **q04, q13, q27**. Regressions:
  **q14, q19, q20, q30**.
- Every run already logs `pre_rerank_order` and `post_rerank_order`
  (`src/index/retrieve.py`), so the evidence is on disk — this phase is
  analysis, not new instrumentation.

### Work

1. **Write an analysis script** (suggested: `src/eval/analyse_rerank.py`,
   runnable as `python -m src.eval.analyse_rerank`). For each of the 7
   flipped questions, print: the question, its gold chunk ids, the gold
   chunk's rank before rerank vs after, and the chunks that displaced it.
2. **Characterise the 4 regressions.** The working hypothesis — stated in
   the Phase 8 write-up but never verified — is that the cross-encoder
   demotes a literal Article-number match that BM25 ranked correctly, in
   favour of a semantically-related but wrong Article. Confirm or refute it
   against the actual logged orderings. Note the question types: q14, q19,
   q20, q30 are all `ordinary_lookup`; q04/q13/q27 span a
   `seeded_contradiction` and lookups. If the split is "reranking helps
   Decision-pair questions and hurts literal Article lookups", that is the
   finding, and it is a genuinely useful one.
3. **Report, don't over-fix.** Write findings to
   `results/rerank_analysis.md`. If, and only if, the cause is unambiguous
   and the fix is small, propose it — but **do not implement a
   query-routing or score-blending scheme in this phase.** Changing
   retrieval mid-plan would invalidate Phase 9's and Phase 11's numbers.
   Recommendation goes in the report; implementation is a separate decision
   for the user.

**Check:** `python -m src.eval.analyse_rerank` runs against the committed
Phase 8 result JSON and prints a rank-movement table for all 7 flipped
questions. An `assert` that the script found exactly the 7 known flips is
enough of a self-check.

**Done when:** `results/rerank_analysis.md` explains the regression with
per-question evidence, and states whether the cross-encoder hypothesis held.

> This phase touches no pipeline code. If you find yourself editing
> `src/rerank/` or `src/index/`, stop — that is out of scope.

---

## Phase 11 — Eval set expansion, re-run, and write-up restatement

**Goal:** more statistical weight, real Superseded Precedent coverage, and a
write-up that reflects Phases 9–10.

### Why it's thin now

- 32 questions; **6 have empty `gold_chunk_ids`** (q08, q09, q10, q24, q25,
  q32), so precision@k scores only 26.
- **1** Superseded Precedent question (q04) — and per Phase 9, that number
  was propped up by a bug.
- `data/controversies.md` has 12 researched controversies; roughly half were
  never turned into questions. Entries 5, 7, 8, 11 are unused or
  under-used.

### Work

1. **Add Superseded Precedent questions — now that Phase 9 makes them
   possible.** Re-run the detector corpus-wide after Phase 9 and pick real
   flagged cases. Target **4–6 total** Superseded questions (up from 1).
   Ground every one in an actual flag, exactly as Phase 8 did — do not write
   a question from the controversy narrative alone. `data/controversies.md`
   entries 9, 10, 11 are Superseded-flavoured leads, but **verify each
   against `article_changes.json` before use**; Phase 8 already found that
   Article 33's *text* never changed across 2023–2025, so entry 9 may not be
   supportable as a Superseded case even though the narrative suggests it.
2. **Give the 6 open-ended questions gold chunk ids where possible.** q08,
   q09, q10, q32 were left open because several valid Decision pairs exist.
   Either pin them to a specific verified pair, or add a distinct
   `expected_flag_article`-style ground truth so they can be scored on
   *something*. q24 is deliberately unanswerable (tests abstention) and q25
   is a combined lookup — those two may legitimately stay unpinned, but say
   so in their `notes`.
3. **Grow toward 45–55 questions.** Keep the existing type balance roughly
   proportional (currently 8 seeded / 4 negative / 20 lookup). **Negative
   Justified Distinction cases matter most** — there are only 4, and
   contradiction *precision* rests entirely on them (ADR 0002). Phase 6's
   suppressed-flag output (420 suppressed pairs corpus-wide) is a rich
   source of verified negatives.
4. **Re-run the full eval on both models.** `python -m src.eval.run_eval
   --model qwen2.5:3b` then `--model qwen2.5:7b`. ~1 hour each, background
   them. Run `--smoke` first, as `PLAN.md` requires.
5. **Restate `results/phase8_writeup.md`.** It currently reports the
   pre-Phase-9 Superseded numbers as though they were meaningful. Either
   revise it in place with a clear note about what changed and why, or
   supersede it with a new write-up that links back. **Do not quietly edit
   the old numbers away** — the bug and its correction are part of the
   story, and the project's own subject matter is superseded precedent.

**Check:** `--smoke` passes end-to-end on the expanded set before the full
run. Additionally assert every question's `gold_chunk_ids` actually exist in
the corpus (a small script; Phase 8 hit exactly this bug with a chunk id
that didn't exist — `reg:2024:sporting:1:40`).

**Done when:** expanded eval set committed, both models re-run, all four
metrics recomputed, write-up restated to reflect Phases 9–11.

---

## Phase 12 — README and portfolio write-up

**Goal:** the thing a recruiter or interviewer actually opens first. Right
now the repo root has `PROJECT_BRIEF.md`, `CONTEXT.md`, `PLAN.md` — all internal
working documents — and **no README**.

**Audience:** a technical reader who has not seen this project, is deciding
in ~60 seconds whether it's substantial, and may then read for 10 minutes.
Not a teammate with context. Write for that person.

### Work

1. **`README.md` at repo root.** Suggested spine:
   - **What it is, in 3 sentences.** A RAG system over FIA F1 regulations and
     Stewards' Decisions that detects *contradictions* between sources rather
     than blending them into one confident answer.
   - **The differentiator, early.** Two named detectors — Divergent Precedent
     and Superseded Precedent (`CONTEXT.md` has the definitions) — plus
     Justified Distinction suppression, which is the precision half.
   - **Headline results table.** Post-Phase-11 numbers, both models,
     including the honest ones (reranking regression, 3B-silent/7B-confident
     faithfulness split). **Do not cherry-pick.** The measured-and-explained
     failures are more credible than clean numbers.
   - **Architecture diagram** (ASCII is fine) of the pipeline stages.
   - **How to run it** — venv, `requirements.txt`, Ollama install + model
     pull, the pipeline commands in order. Note `pdftotext` and Python 3.11
     (`docs/RECON.md`). Someone must be able to reproduce this.
   - **Engineering decisions worth defending**, linked to the ADRs: numpy
     over FAISS (ADR 0001), two detectors with precision reported alongside
     recall (ADR 0002).
   - **Limitations**, verbatim in spirit from `PLAN.md`'s list plus what
     Phases 9–11 added. This section is a strength, not an apology.
2. **Link, don't duplicate.** `CONTEXT.md`, `PLAN.md`, `docs/RECON.md`,
   `docs/adr/`, and the results JSON stay where they are; the README points
   at them.
3. **Consider a worked example.** One real query, showing retrieved chunks →
   contradiction flag → final structured JSON answer. Pull a genuine one from
   `results/*_generation.json` rather than inventing it. This does more to
   convey what the system does than any description.
4. **Optional, only if the user wants it:** the FastAPI + minimal UI that
   `PROJECT_BRIEF.md` lists as optional. **Ask before building it** — it's a
   different kind of work than the rest of this plan, and a good README may
   make it unnecessary. If built, keep it in `app/` (the directory exists and
   is empty), keep it thin, and don't let it become a second codebase.

**Check:** no code to test. Instead: follow the README's own setup
instructions from a clean shell and confirm each command works as written.
A README with a command that doesn't run is worse than no README.

**Done when:** `README.md` is committed and its instructions have been
executed, not just proofread.

---

## Notes carried forward

- **`q24` is load-bearing.** It asks about Article 12.2.1, an International
  Sporting Code Article deliberately absent from the corpus, to test whether
  the system abstains instead of hallucinating. 7B correctly abstained.
  Keep it, and keep its `notes` explaining why it looks broken but isn't.
- **Don't delete old result files.** `results/` holds a pre-fix Phase 8 run
  (`*_20260923T011354_*`) with 21 generation failures. It documents a real
  bug. `PLAN.md`'s logging rule is "reproducibility is the point."
- **The corpus has no 2026 data**, so section-prefixed Article IDs
  (`C3.14.4`) are handled by the parsers but never exercised on real data.
  Don't remove that handling as dead code; do mention it as untested.
