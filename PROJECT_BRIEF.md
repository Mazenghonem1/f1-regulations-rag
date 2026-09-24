# F1 Regulations & Stewards' Decisions RAG — Project Brief

## What this project is

A Retrieval-Augmented Generation system over F1's Sporting/Technical Regulations
and FIA Stewards' Decisions. The system answers rules questions with cited
sources, and — its key differentiator — explicitly detects and surfaces
**contradictions** between retrieved sources (e.g. a 2023 penalty precedent vs.
a 2024 regulation change, or two stewards' panels ruling differently on
similar incidents), instead of silently blending them into one confident
answer.

This is a personal portfolio project. It pairs with an existing project,
"F1 Tyre Wear Prediction" (predictive ML), to show range: prediction → now
retrieval/reasoning over unstructured regulatory text.

## Hard constraint: zero paid API usage

Everything must run on free/local tooling. No OpenAI/Anthropic/Cohere API
keys, no paid vector DB tiers, no paid reranker APIs. Use:

- **Embeddings**: `sentence-transformers` locally — `BAAI/bge-small-en-v1.5`
  (good quality/speed tradeoff, free, runs on CPU) or
  `sentence-transformers/all-MiniLM-L6-v2` (faster/lighter fallback).
- **Vector store**: FAISS, local, in-process. No hosted service.
- **Reranker**: `cross-encoder/ms-marco-MiniLM-L-6-v2` via
  `sentence-transformers`, local, free.
- **Generation LLM**: run locally via **Ollama**. Recommended models
  (pick based on available RAM/VRAM): `llama3.1:8b`, `qwen2.5:7b`, or
  `mistral:7b`. If local hardware can't handle 7-8B models comfortably,
  fall back to `llama3.2:3b` or a quantized GGUF variant.
- **LLM-as-judge for eval**: reuse the same local Ollama model — no need
  for a separate paid judge model. Note in the write-up that this is a
  known limitation (weaker judge than GPT-4-class), and that's fine to
  be upfront about.
- **Hybrid search (BM25)**: `rank_bm25` (pure Python, free) combined with
  FAISS dense retrieval.

Before building: confirm Ollama is installed and a model is pulled before
building the generation module. If it isn't installed, stop and tell the
user to run `ollama pull llama3.1:8b` (or the chosen model) first — don't
silently fall back to a paid API.

## Data sources (all public, no auth required)

1. **FIA Sporting Regulations** (current + last 2-3 seasons) — PDF,
   fia.com > F1 > Regulations.
2. **FIA Technical Regulations** (current + last 2-3 seasons) — PDF,
   same location.
3. **FIA Stewards' Decisions** — published per Grand Prix as individual
   PDFs (e.g. "Doc 15 - Offence - Car 1 - Track Limits"), archived on the
   FIA website per-event. These are the "messy" layer: short, inconsistent
   formatting, heavy jargon, cross-references to specific Articles.

Target corpus size for v1: 3 seasons of regulations + stewards' decisions
from ~10-15 Grands Prix (enough decisions to have genuine precedent
overlaps and contradictions, without needing to scrape everything).

Scraper must:
- Respect FIA site's robots.txt and rate-limit requests.
- Preserve metadata per document: season/year, Grand Prix (if applicable),
  document type (regulation vs. decision), publication date, and for
  regulations, the Article number structure.
- Store raw PDFs + extracted text separately, so re-chunking doesn't
  require re-scraping.

## Pipeline architecture

```
Scrape → Parse/Extract → Chunk (structure-aware) → Embed → Index (FAISS + BM25)
   → Hybrid Retrieve → Rerank (cross-encoder) → Contradiction Check
   → Generate (local LLM, citation-grounded) → Eval (retrieval + faithfulness)
```

### Chunking
- Regulations: split by Article (and sub-clause where identifiable), not
  raw token windows. Preserve the Article number in chunk metadata — this
  is what citations will point to.
- Stewards' Decisions: each decision doc is short enough to often be one
  chunk, but split multi-incident decisions into per-incident chunks.
  Preserve: date, Grand Prix, car number, cited Article(s), and the
  penalty outcome as structured metadata fields (not just free text) —
  this metadata is what makes contradiction detection tractable later.

### Retrieval
Hybrid: BM25 (catches exact Article number / driver / team lookups, which
dense embeddings are often bad at) + dense FAISS retrieval, combined via
reciprocal rank fusion. Retrieve top ~20 candidates before reranking.

### Reranking
Cross-encoder reranks the top ~20 down to top ~5-8 passed to generation.
Log rank changes (pre-rerank vs post-rerank order) — this becomes part of
the eval story later ("reranking changed the top result in X% of queries").

### Contradiction detection (the differentiator — build this deliberately, don't bolt it on)
After retrieval/reranking, before generation:
1. Group retrieved chunks by whether they're regulation text vs. decision
   precedent.
2. If two or more retrieved *decision* chunks address similar incident
   types (use metadata: similar cited Article + similar penalty category)
   but have **different outcomes**, flag it.
3. If a retrieved *decision* predates a retrieved *regulation* chunk's
   effective date and that regulation superseded the relevant Article,
   flag it as potentially outdated precedent.
4. Pass these flags into the generation prompt explicitly, and require
   the LLM's structured output to surface them rather than silently pick
   one source.

This is the part to spend real design time on — it's the whole point of
the project, not a nice-to-have.

### Generation
Local LLM via Ollama. Prompt must:
- Answer only from retrieved context (no outside knowledge).
- Output structured JSON: `{answer, citations: [{doc_id, article_or_decision, quote_or_paraphrase}], contradictions_flagged: [...]}`.
- Explicitly state uncertainty when contradiction flags are present, rather
  than averaging conflicting sources into one confident-sounding answer.

## Evaluation (this is what makes it resume-worthy — don't skip it)

Build a hand-written eval set of ~30-40 questions, including a deliberate
subset (~8-10) that hit **known contradictory or superseded precedent** —
you'll need to research a few real controversial stewarding calls
(e.g. track limits inconsistency, safety car restart calls) to seed these.

Metrics to compute and report:
- **Retrieval precision@k** (does the correct source appear in top-k),
  measured before and after adding reranking — get a concrete delta.
- **Citation faithfulness** — does the generated citation actually appear
  in / support what was retrieved? Score with the local LLM as judge
  against a rubric, or manually for the smaller eval set.
- **Contradiction recall** — of the questions you deliberately seeded with
  known contradictions, what fraction did the system correctly flag?
  This is your headline metric; no standard library computes this, you're
  building the harness yourself, which is a legitimate engineering
  contribution to call out.
- **Baseline comparison** — run the same eval questions against the local
  LLM with *no retrieval at all*, to show retrieval's marginal value on a
  domain-specific enough dataset that base-model knowledge alone is
  visibly insufficient.

## Suggested build order (roughly 4 weeks, adjust as needed)

1. **Week 1**: Scraper + PDF parsing + structure-aware chunking. Get a
   clean, metadata-rich corpus of ~150-300 chunks. Manually sanity-check
   chunk quality on a sample.
2. **Week 2**: Embedding + FAISS index + BM25 + hybrid retrieval. Try 10-15
   manual queries, eyeball whether retrieval looks reasonable.
3. **Week 3**: Reranking + contradiction detection logic + local LLM
   generation with structured/citation-grounded output via Ollama.
4. **Week 4**: Build the eval set (including seeded contradictions), run
   full evaluation, compute all four metrics above, write up results.
   Optional: wrap in a small FastAPI + simple frontend (Streamlit or a
   minimal HTML page) for demo-ability in interviews.

## Repo structure (suggested)

```
f1-rag/
├── PROJECT_BRIEF.md
├── data/
│   ├── raw/              # scraped PDFs
│   ├── processed/        # extracted text + metadata JSON
│   └── eval_set.json      # hand-written eval questions + gold answers/citations
├── src/
│   ├── scrape/
│   ├── chunk/
│   ├── index/             # FAISS + BM25 build/query
│   ├── rerank/
│   ├── contradiction/     # the core differentiator logic
│   ├── generate/          # Ollama prompting + structured output parsing
│   └── eval/              # precision@k, faithfulness, contradiction recall, baseline
├── results/                # eval run outputs, metrics over time
└── app/                    # optional FastAPI + minimal UI
```

## Notes for whoever (or whatever) builds this

- Keep each pipeline stage (retrieve / rerank / contradiction-check /
  generate) as an independently callable, testable module — not one
  monolithic script. The eval harness needs to swap stages on/off
  (e.g. "with vs without reranking") to produce the before/after numbers.
- Log everything (which chunks were retrieved, rerank scores, contradiction
  flags raised) to `results/` per eval run so the numbers are reproducible
  and can be pasted into a write-up later.
- Confirm Ollama + the chosen model are actually installed before writing
  the generation module; don't assume.
- No paid API keys anywhere in this project. If a library defaults to
  OpenAI unless configured otherwise (e.g. some Ragas setups), explicitly
  configure it to use the local Ollama model instead, or write a small
  custom eval harness rather than fighting a library's cloud-first
  defaults.
