# F1 Regulations & Stewards' Decisions RAG

A Retrieval-Augmented Generation system over FIA Formula 1 Sporting/Technical
Regulations and FIA Stewards' Decisions. It answers rules questions with
cited sources — and, its actual point, it detects and surfaces
**contradictions** between retrieved sources instead of silently blending
them into one confident answer. Everything runs on free, local tooling: no
paid API keys anywhere.

## The differentiator

Most RAG demos stop at "retrieve, then generate." This one adds a
contradiction-detection stage between retrieval and generation, because the
source material actually contradicts itself in two distinct, measurable
ways:

- **Divergent Precedent** — two Stewards' panels citing the same Article on
  materially similar incidents, reaching different Outcomes. A disagreement.
- **Superseded Precedent** — a Decision applying an Article that was later
  amended, so it no longer reflects the current rule. Not a disagreement — a
  timeline problem.
- **Justified Distinction** — different Outcomes that are *correct* because
  the facts differ (wet vs dry, repeat offence, intent). This suppresses a
  Divergent Precedent flag rather than counting as one. F1 penalties
  legitimately escalate and vary; a detector that can't tell the difference
  scores recall 1.0 by flagging everything, which is worthless. See
  [ADR 0002](docs/adr/0002-contradiction-types-and-precision.md).

## Headline results

45-question eval set (13 seeded contradictions, 7 negative Justified
Distinction cases, 25 ordinary lookups), both models CPU-only on an Intel
Mac. Full numbers, per-question detail, and the story behind each one:
[`results/evaluation.md`](results/evaluation.md).

| Metric | qwen2.5:3b | qwen2.5:7b |
|---|---|---|
| Retrieval precision@8, exact (no rerank / reranked) | 0.694 / 0.694 | identical — retrieval is generation-model-independent |
| Retrieval precision@8, article-level (any Issue of the gold Article) | **1.0** (15/15) | identical |
| Divergent Precedent recall / precision | **0.889 / 1.0** | identical |
| Superseded Precedent recall / precision | 1.0 / 1.0 | identical |
| Citations produced (of 45 questions) | 28 citations, 13 questions | 100 citations, 41 questions |
| Citation faithfulness (LLM-judge) | **0.679** | **0.37** |

Reported without cherry-picking:

- **Reranking is a wash here, and now explained.** It flips 8 of 36 scored
  questions (4 up, 4 down) for a net-zero precision change. Root-caused in
  [`results/rerank_analysis.md`](results/rerank_analysis.md): the corpus
  keeps every historical Issue of every amended Article as its own chunk
  (needed for observable change history), so heavily-amended Articles have
  20+ near-duplicate chunks competing for rank. The cross-encoder reshuffles
  among these near-identical Issues close to arbitrarily — it never promotes
  a genuinely wrong Article, which was the original (wrong) hypothesis. The
  same mechanism explains most of the exact-metric's precision@8 gap: a
  second, article-level metric (credit any Issue of the gold Article, not
  just one pinned Issue) scores a clean **1.0** on every eligible question —
  retrieval is finding the right regulatory content nearly every time; the
  exact number understates that.
- **3B is silent, 7B is confidently wrong** — direction holds, magnitude
  varies run to run (Ollama sampling is unseeded; 7B's faithfulness has
  ranged 0.263–0.462, 3B's 0.679–0.971, across recent runs). qwen2.5:3b is
  consistently the more conservative, more faithful model; qwen2.5:7b
  consistently cites more often at a much lower faithfulness rate, traced
  concretely to cross-chunk conflation when several near-identical Decisions
  sit together in context.
  Neither is flattering; both are real and worth knowing before you pick a
  model size for a legal/compliance-adjacent domain. Full numbers and the
  run-to-run variance caveat: [`results/evaluation.md`](results/evaluation.md).
- **A three-bug chain, found and fixed in sequence, not hidden:** an outcome-
  normalisation bug and a retrieval-depth gap in Divergent Precedent were
  fixed first, which raised recall (0.667 → 0.889) but exposed a third,
  separate metric-granularity bug that cost precision (0.75 → 0.667) — the
  detector's own flags were still correct, but the eval scored "any flag for
  this Article" instead of "the specific pair this question is about."
  Fixing that (plus two more real regex bugs found while verifying it)
  brought precision back to **1.0** with no loss of recall. A semantic
  (embedding-similarity) alternative was tried and measured before being
  rejected with evidence — it couldn't reliably separate "same penalty,
  reworded" from "different penalty, same template" on this corpus. The
  full chain is documented, not smoothed over, in the write-up.

## Architecture

```
Scrape (fia.com) → Parse/Extract (pdftotext) → Chunk (structure-aware,
by Article / by Decision)
        │
        ▼
Embed (bge-small-en-v1.5) ──┐
                            ├─→ Hybrid Retrieve (reciprocal rank fusion)
BM25 (rank_bm25) ───────────┘         │
                                       ▼
                          Rerank (cross-encoder, top 20 → top 8)
                                       │
                                       ▼
                    Contradiction Check (Divergent / Superseded /
                       Justified-Distinction suppression)
                                       │
                                       ▼
                Generate (local Ollama, JSON-schema-constrained,
                    citation-grounded, flags surfaced explicitly)
                                       │
                                       ▼
                Eval (precision@k, faithfulness, contradiction
                    recall/precision, no-retrieval baseline)
```

Each stage (`src/index`, `src/rerank`, `src/contradiction`, `src/generate`,
`src/eval`) is independently callable and testable — the eval harness turns
reranking on/off and diffs the result rather than re-deriving it by hand.

## How to run it

Requires Python 3.11 (not the system 3.13 — see
[ADR 0001](docs/adr/0001-numpy-brute-force-over-faiss.md)), `pdftotext`
(`brew install poppler` / `apt install poppler-utils`), and
[Ollama](https://ollama.com) installed locally.

```bash
python3.11 -m venv .venv
.venv/bin/pip install -r requirements.txt

ollama pull qwen2.5:3b     # or qwen2.5:7b — both are used in the eval
ollama serve               # if not already running

# Pipeline, in order:
.venv/bin/python -m src.scrape.run              # fetches FIA PDFs, rate-limited
.venv/bin/python -m src.chunk.run               # extracts + chunks + builds article_changes.json
.venv/bin/python -m src.eval.run_eval --smoke   # 3-question sanity check first
.venv/bin/python -m src.eval.run_eval --model qwen2.5:3b   # full run, ~1hr CPU-only
```

Self-checks (no test framework, just `assert`-based scripts):

```bash
.venv/bin/python -m src.contradiction.test_contradiction
.venv/bin/python -m src.eval.test_eval_set
.venv/bin/python -m src.eval.analyse_rerank
```

### Minimal demo UI

A thin FastAPI wrapper (`app/main.py`) around the same pipeline stages, with
a single-page HTML frontend (`app/static/index.html`, no build step, no JS
framework) — for demo-ability, not a second codebase. Ask a question, see
the retrieved chunks, contradiction flags, and citation-grounded answer.

```bash
.venv/bin/uvicorn app.main:app --reload
# open http://127.0.0.1:8000
```

Answers take a while on CPU-only hardware (RECON.md: ~8-12 tok/s for
qwen2.5:3b) — the UI says so rather than looking stuck.

## A worked example

**q34**: *"Does the 2023 Qatar Grand Prix Decision (Document 70, citing
Article 48.1) still reflect the current rule on judging a jump start?"*

Retrieval surfaces `dec:2023:Qatar Grand Prix:70` (cites Article 48.1,
dated 2023-10-08) alongside regulation chunks. The contradiction stage
runs `detect_superseded_precedent` and finds Article 48.1 was amended on
2024-07-31 — after the Decision — and flags it:

```json
{
  "type": "superseded_precedent",
  "article": "48.1",
  "match_granularity": "article",
  "decision": "dec:2023:Qatar Grand Prix:70",
  "decision_date": "2023-10-08",
  "changed_on": "2024-07-31",
  "from_issue": 6, "to_issue": 7
}
```

The flag is passed into the generation prompt explicitly. qwen2.5:7b's
final answer: *"No"* — with a citation naming the amendment dates rather
than averaging the old and new rule into one confident-sounding paragraph.
(The actual sub-clause change, verified by hand for this question: Article
48.1's transponder-detection clause for judging a jump start was removed
in that amendment — a real narrowing of the rule, not renumbering noise.)
Full generation output: `results/eval_qwen2.5_7b_full_20260923T181153_generation.json`.

## Engineering decisions worth defending

- **numpy exact search instead of FAISS** — at ~1,700 chunks the entire
  embedding matrix is a few MB and exact cosine similarity is a single
  matrix multiply, sub-millisecond and *more* accurate than an approximate
  index. FAISS is the right answer somewhere around 10⁵ vectors; the
  retriever interface is narrow enough to drop it in later without touching
  callers. [ADR 0001](docs/adr/0001-numpy-brute-force-over-faiss.md).
- **Two contradiction detectors, precision reported alongside recall** — a
  single "contradiction recall" metric is trivially gamed by a detector
  that flags every same-Article pair. Justified Distinction suppression
  exists because F1 penalties legitimately vary, and the negative eval
  cases that make suppression measurable were the actual engineering work.
  [ADR 0002](docs/adr/0002-contradiction-types-and-precision.md).
- **Sub-clause citation normalisation with an honest precision cost** —
  Decisions cite sub-clauses (`33.3`); the change-history table is keyed by
  top-level Article (`33`), because chunking Regulations at sub-clause
  granularity would hurt retrieval. Rather than silently guessing, every
  Superseded Precedent flag carries `match_granularity` (`"exact"` vs
  `"article"`) so the reader can see that an Article-level match doesn't
  prove the specific sub-clause changed.

## Limitations

- **The LLM-judge for faithfulness is qwen2.5:3b judging qwen2.5-family
  output** — not GPT-4-class evaluation. Faithfulness numbers are
  directional, not precise.
- **The eval set (45 questions) is self-authored**, including the negative
  cases contradiction precision depends on entirely.
- **"Materially similar incident" is a judgment call**, encoded as a 0.75
  Fact-embedding-similarity threshold, not an FIA rule.
- **Divergent Precedent's outcome comparison doesn't recognise semantically
  equivalent outcomes phrased differently** (see Headline Results above) —
  a known, documented gap, not fixed yet.
- **No 2026 data is in the corpus** — the 2026 season restructured Article
  numbering to a section-prefixed form (`C3.14.4`). The parsers handle it
  (`src/contradiction/article_ids.py`), but it's untested against real data.
- **CPU-only inference on 2020 Intel hardware** (~2-4 tok/s on the 7B model)
  shaped the eval set size as much as any methodological choice — a full
  run is roughly an hour per model.

Full detail, per-run numbers, and the story behind every one of these:
[`results/evaluation.md`](results/evaluation.md). Project glossary:
[`CONTEXT.md`](CONTEXT.md). Environment facts this build was verified
against: [`docs/RECON.md`](docs/RECON.md).
