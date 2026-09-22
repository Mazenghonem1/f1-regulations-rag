# Implementation Plan

Planned with Opus, executed with Sonnet, one phase per session.
Decisions settled in the grilling session of 2026-09-22; see `CONTEXT.md` for
vocabulary and `docs/adr/` for the two overrides of `CLAUDE.md`.

## Ground rules for the executing agent

- **Read `CONTEXT.md` first.** Use its terms exactly. "Contradiction" is an
  umbrella, never a detector name.
- **Every phase ends with a runnable check** — an `assert`-based `__main__`
  self-check or one small `test_*.py`. No test frameworks, no fixtures.
- **Stop at a phase boundary** and report. Do not roll into the next phase.
- **No paid APIs anywhere.** No OpenAI/Anthropic/Cohere keys, no hosted vector
  DB, no hosted reranker. If a library defaults to a cloud provider, configure
  it to local or replace it.
- **Commit at each phase end.** Repo is not yet initialised; Phase 0 does that.
- Verified environment facts are in `docs/RECON.md`. Trust them over guessing;
  re-verify anything that looks stale.

## Settled decisions

| Area | Decision |
|---|---|
| Generation model | `qwen2.5:3b` for iteration; one final `qwen2.5:7b` run for headline numbers |
| Ollama | Absent. Deferred to Phase 5, hard-gated in code |
| Python | Pin 3.11 (3.13 risks wheel gaps on Intel Mac) |
| Dense retrieval | Exact numpy cosine, behind a swappable interface (ADR 0001) |
| Corpus source | Pluggable; fia.com canonical with `Crawl-delay: 10`, mirror as dev cache |
| Decision parsing | Fuzzy labels + coverage report as a first-class artifact |
| Supersession | Derived from real issue-diffs, not heuristics |
| Corpus scope | 3 seasons raw, ~12 controversy-targeted events processed |
| Contradictions | Two named detectors; precision reported alongside recall (ADR 0002) |

---

## Phase 0 — Environment and skeleton

**Goal:** a working 3.11 venv and a repo that runs.

1. Install Python 3.11 (`brew install python@3.11`), create `.venv`.
2. `git init`; `.gitignore` excluding `.venv/`, `data/raw/`, `__pycache__/`.
3. `requirements.txt`: `requests`, `beautifulsoup4`, `pdfminer.six`,
   `sentence-transformers`, `rank_bm25`, `numpy`. **No faiss.**
4. Directory skeleton per `CLAUDE.md`, plus `data/raw/`, `data/processed/`,
   `results/`.

**Check:** a script that imports every dependency and asserts Python is 3.11.

**Done when:** the import check passes inside the venv.

---

## Phase 1 — Controversy research (do this before the scraper)

**Goal:** know which events contain real contradictions *before* spending
effort acquiring them. This de-risks the whole project — discovering a corpus
with no contradictions in Phase 6 would be fatal; discovering it here is cheap.

1. Research 10–12 documented F1 stewarding controversies, 2023–2025. Target
   **Divergent Precedent** candidates (track limits applied inconsistently,
   unsafe releases, impeding in qualifying, safety-car restarts) and
   **Superseded Precedent** candidates (Articles amended between seasons).
2. For each: the event, approximate date, cars involved, likely Article, and
   *why* it is contested.
3. Write `data/controversies.md` — human-readable, with sources.

**Check:** none needed; this is research. Sanity bar is 10+ entries, each
naming a specific event and a plausible Article.

**Done when:** the event list is ready to drive Phase 2's scrape targets.

> Hand this to a research subagent with web access. It is the one phase where
> being wrong is expensive later and cheap now.

---

## Phase 2 — Scraper

**Goal:** raw PDFs on disk, with provenance.

1. `src/scrape/` with a pluggable source: `fia` (canonical) and `mirror`
   (`TracingInsights/DDocs`, dev cache only).
2. **Honour `Crawl-delay: 10`** on fia.com. Non-negotiable.
3. Handle **both URL eras** — `/system/files/` + underscores (2025+) and
   `/sites/default/files/` + spaces, URL-encoded (≤2024). Missing this
   silently halves the corpus.
4. Scrape season/event slugs from the dropdowns; **never construct them**
   (`season-2026-2071` and `-2072` both exist and differ).
5. Decisions: filter filenames on `decision|infringement|offence|protest` —
   only ~11–17 of ~55 per-event PDFs are Decisions.
6. Regulations: fetch **all issues** for 2023–2025 from
   `/regulation/category/110`, not just the latest. Phase 4 needs the history.
7. Store raw PDFs separately from anything extracted; record source URL and
   fetch date per file.

**Check:** `test_scrape.py` — era-routing picks the right URL pattern per year;
the Decision filename filter accepts known Decisions and rejects a
classification document.

**Done when:** 3 seasons of raw PDFs on disk; targeted events prioritised.

> Scrape all three seasons raw even though only ~12 events get processed.
> Storage is free; re-scraping at 10s/request is not.

---

## Phase 3 — Parse and chunk

**Goal:** structured, metadata-rich chunks. **The highest-risk phase** —
everything downstream inherits these errors.

1. Extract text with `pdftotext -layout` (verified present) or `pdfminer.six`.
2. **Regulations:** split by Article, not token windows. Parse **both** ID
   forms — bare `33.3` and section-prefixed `C3.14.4`. Article ID is the
   citation target and belongs in chunk metadata.
3. **Decisions:** parse the fixed label vocabulary (`No / Driver`,
   `Competitor`, `Session`, `Fact`, `Infringement`, `Decision`, `Reason`)
   with **fuzzy matching** — `Infringement` is misspelled `Infringment` in at
   least one 2023 document. Join continuation lines.
4. Extract as structured fields: event, date, car number, driver, session,
   **cited Article(s)** (from `Infringement`), **Outcome** (from `Decision`).
   "No further action" is an Outcome, not a null.
5. **Dedupe by extracted Document number, not filename** — `_0` suffixed
   near-duplicates exist.
6. **Emit a coverage report** to `results/` — per-field extraction rates, with
   failures listed. This is how you know the phase actually worked.

**Check:** `test_parse.py` — fuzzy label matcher handles the `Infringment`
misspelling; both Article ID forms parse; dedupe collapses a known duplicate
pair.

**Done when:** coverage report shows **>90%** of Decisions yielding both a
cited Article and an Outcome. Below that, fix the parser before proceeding —
do not carry the gap forward.

---

## Phase 4 — Article change history

**Goal:** dated ground truth for Superseded Precedent.

1. For each Article, diff consecutive Regulation Issues.
2. Emit `data/processed/article_changes.json`: Article ID → list of
   `{changed_on, from_issue, to_issue, change_summary}`.
3. Normalise across the 2026 notation change so an Article can be tracked
   across the boundary where possible; record explicitly where it cannot.

**Check:** `test_article_changes.py` — a known unchanged Article reports no
change; a known amended one reports a change with a plausible date.

**Done when:** the change table covers every Article cited by the Phase 1
controversies.

> This is what turns `CLAUDE.md`'s vaguest contradiction rule into a fact
> rather than a guess. Fall back to hand-coding supersession for eval-set
> Articles only if the diff proves intractable.

---

## Phase 5 — Index and hybrid retrieval

**Goal:** working retrieval. No LLM needed.

1. Embed chunks with `BAAI/bge-small-en-v1.5` (CPU; cache to disk — Intel Mac,
   this is slow, do it once).
2. Dense retrieval: **exact numpy cosine** behind a retriever interface
   (ADR 0001). No FAISS.
3. BM25 via `rank_bm25` — carries exact Article-number and driver lookups,
   which embeddings handle poorly.
4. Fuse with reciprocal rank fusion; return top ~20.
5. Rerank top 20 → top 5–8 with `cross-encoder/ms-marco-MiniLM-L-6-v2`.
   **Log pre- and post-rerank order** — the delta is an eval result.
6. Retrieval and reranking must be independently callable, and reranking must
   be switchable off. The eval harness needs both configurations.

**Check:** `test_retrieval.py` — a literal Article-number query ranks the exact
Article first (this is the BM25 half earning its place); RRF handles one
retriever returning nothing.

**Done when:** 10–15 manual queries return plausible chunks, eyeballed.

---

## Phase 6 — Contradiction detection

**Goal:** the differentiator. Two detectors, named per `CONTEXT.md`.

1. **Divergent Precedent:** group retrieved Decision chunks by cited Article;
   flag differing Outcomes on materially similar incidents.
2. **Justified Distinction suppression:** before flagging, check for
   Mitigating Factors — wet vs dry, repeat offence, session, intent. **This is
   the precision half and it is not optional** (ADR 0002).
3. **Superseded Precedent:** a Decision's date against
   `article_changes.json` — flag when the cited Article changed after the
   Decision.
4. Emit structured flags with the evidence that triggered them, and log every
   flag to `results/`.

**Check:** `test_contradiction.py` — two Decisions, same Article, different
Outcomes → flagged; the same pair with a Mitigating Factor present → **not**
flagged; a Decision predating an Article change → superseded.

**Done when:** both detectors fire correctly on hand-built fixtures.

> Build the suppression logic in the same phase as the detector, not after.
> A detector without it has no precision floor and the headline metric becomes
> meaningless.

---

## Phase 7 — Generation

**Goal:** citation-grounded structured output.

**Gate first:** ping `localhost:11434`. If Ollama is absent, **raise an error
naming the exact `ollama pull qwen2.5:3b` command and stop.** No fallback to a
paid API — this gate is real code, not a comment.

1. Prompt: answer only from retrieved context; no outside knowledge.
2. Structured JSON output:
   `{answer, citations: [{doc_id, article_or_decision, quote_or_paraphrase}], contradictions_flagged: [...]}`
3. Pass contradiction flags into the prompt **explicitly**; require the model to
   surface them rather than silently pick a source.
4. Parse defensively — a 3B model will occasionally emit malformed JSON. Retry
   once, then fail loudly rather than silently dropping a flag.

**Check:** `test_generate.py` — the Ollama gate raises with a useful message
when the service is down; the JSON parser handles a known-malformed response.

**Done when:** a real query returns valid structured JSON with citations
traceable to retrieved chunks.

---

## Phase 8 — Evaluation

**Goal:** the numbers. This is the resume-worthy part.

1. **Eval set** (`data/eval_set.json`), 30–40 questions:
   - ~8–10 **Seeded Contradictions** from Phase 1's research
   - **Negative cases** — Justified Distinctions where the correct behaviour
     is *not* to flag. Required for precision (ADR 0002); easy to forget.
   - The remainder: ordinary regulation lookups
2. **Metrics:**
   - Retrieval precision@k, **with and without reranking** — report the delta
   - Citation faithfulness — local LLM as judge against a rubric
   - **Contradiction recall *and* precision**, reported per detector
   - **Baseline:** same questions, no retrieval, to show retrieval's marginal
     value
3. Log every run to `results/` — retrieved chunks, rerank scores, flags raised.
   Reproducibility is the point.
4. Iterate on `qwen2.5:3b`. Final run on `qwen2.5:7b`; **report both** — the
   3B/7B delta is a more interesting result than either number alone.

**Check:** the harness runs end-to-end on 3 questions before the full set.

**Done when:** all metrics computed, both models run, results written up.

---

## Known limitations to state plainly in the write-up

Naming these is stronger than hoping nobody asks.

- **The judge is weak.** `qwen2.5` judging its own family's output is not
  GPT-4-class evaluation. Say so.
- **The eval set is small and self-authored.** 30–40 hand-written questions
  by the system's own author. Contradiction precision is measured against
  negative cases that same author chose.
- **Contradiction ground truth is interpretive.** Whether two incidents are
  "materially similar" is a judgement call, made here by one person who is not
  an FIA steward.
- **FAISS was specified and deliberately not used** (ADR 0001).
- **CPU-only inference on 2020 Intel hardware** shaped the model choice. The
  3B/7B delta quantifies what that cost.
- **Mirror provenance:** `TracingInsights/DDocs` declares no license. Used as a
  development cache only; corpus of record comes from fia.com. Do not
  redistribute the PDFs.
