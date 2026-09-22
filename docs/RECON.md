# Environment reconnaissance

Verified 2026-09-22 by direct fetch and extraction. Trust these over guessing;
re-verify anything that looks stale.

## Local machine

| | |
|---|---|
| Hardware | MacBookPro16,2 — Intel i7-1068NG7, 16GB, **no GPU** |
| Python | 3.13.3 system. **Pin 3.11** — 3.11 is not yet installed |
| `pdftotext` | Present at `/usr/local/bin/pdftotext` |
| Also present | `pdfminer.six`, `pypdf`. **`pymupdf` is not** |
| Ollama | **Not installed.** Blocks Phase 7 only |

CPU-only inference: an 8B model runs ~2–4 tok/s here, a 3B ~8–12 tok/s. This
drove the `qwen2.5:3b` choice.

## fia.com access

**No bot protection.** It is CloudFront (AWS CDN) caching, not Cloudflare. No
challenge, no JS interstitial. Tested: 8 rapid sequential requests with UA
`python-requests/2.31.0` → all HTTP 200; a request with **no User-Agent at
all** → HTTP 200. `requests` + `BeautifulSoup` is sufficient. No Playwright, no
`cloudscraper`, no UA spoofing.

**robots.txt** (stock Drupal 7, `last-modified: 2025-01-22`): single `*` group,
**`Crawl-delay: 10`**. Both target path families are permitted — `/documents/…`,
`/system/files/decision-document/*.pdf`, `/sites/default/files/…`,
`/regulation/category/110`. But `Disallow: */node` matches any path segment
ending in `node` — **use the `/documents/…` aliases, never canonical
`/node/<id>` URLs.**

At 10s/request a full 3-season corpus is roughly 4–7 hours single-threaded.

## Regulations

Landing page `https://www.fia.com/regulation/category/110` is server-rendered
HTML, **243 `.pdf` links**, and retains *every* historical issue — not just
current. Verified resolving and extracting:

| URL | Pages | Chars |
|---|---|---|
| `/system/files/documents/fia_2026_f1_regulations_-_section_b_sporting_-_iss_08_-_2026-08-05_7.pdf` | 98 | 280,072 |
| `/sites/default/files/fia_2023_formula_1_sporting_regulations_-_issue_1_-_2022-07-19.pdf` | — | 306,911 |

Filenames encode season, section, issue number and effective date — metadata
without opening the file.

**2026 restructure:** `fia_YYYY_formula_1_sporting_regulations_-_issue_N`
became lettered sections `fia_2026_f1_regulations_-_section_B_sporting_-_iss_08`
(A General, B Sporting, C Technical, D/E Financial, F Operational).

`pdftotext -layout` preserves Article numbering cleanly, so article-aware
chunking works.

## Stewards' decisions

Per-event listing pages are **server-rendered HTML** — no headless browser:

```
https://www.fia.com/documents/championships/fia-formula-one-world-championship-14/season/<SEASON_SLUG>/event/<Event%20Name>
```

**Season slugs are opaque; scrape them from the `<option>` dropdowns, never
construct them.** 2026 `season-2026-2072`, 2025 `season-2025-2071`, 2024
`season-2024-2043`, 2023 `season-2023-2042`, 2022 `season-2022-2005`.

> **Trap:** `season-2026-2071` and `season-2026-2072` both exist and differ —
> `-2071` serves 2025 content. Use `-2072` for 2026.

**PDFs are text-based, not scanned. No OCR needed.** Verified: 2025 Abu Dhabi
Car 4 decision, 2 pages, embedded TrueType (`IJILQW+ArialMT`); `pdfimages
-list` shows only a 1202×107 JPEG letterhead, not a page scan. 1,778 chars
extracted. A 2023 doc also verified (1,253 chars).

Extraction yields a near-parseable record:

```
2025 ABU DHABI GRAND PRIX          05 - 07 December 2025
From The Stewards        Document 48
No / Driver   4 - Lando Norris
Competitor    McLaren Formula 1 Team
Session       Race
Fact          Car 4 left the track … and allegedly gained a lasting advantage.
Infringement  Breach of Article 33.3 of the FIA Formula One Sporting Regulations.
Decision      No further action.
Reason        The Stewards reviewed positioning/marshalling system data, video …
```

`Infringement` reliably contains the cited Article; `Decision` the Outcome.

**Parsing traps:**
- The label is misspelled **`Infringment`** in at least one 2023 document —
  match fuzzily.
- Genuine near-duplicates exist (`…pit lane speeding.pdf` *and*
  `…pit lane speeding_0.pdf` in the same event) — **dedupe by extracted
  Document number, not filename.**

**Volume:** ~53–57 PDFs per event, of which only **11–17 are actual Decisions**
(rest are classifications, scrutineering, event notes). Filter on
`decision|infringement|offence|protest`. So 10–15 events ≈ 150–250 Decisions.

## Two URL eras — the easiest thing to get wrong

A single-pattern scraper silently misses half the corpus.

| Era | Path | Filename style |
|---|---|---|
| 2025+ | `/system/files/…` | underscores, lowercase |
| ≤2024 | `/sites/default/files/…` | spaces, title case (**URL-encode**) |

Examples:
- `/sites/default/files/decision-document/2023 Monaco Grand Prix - Infringement - Car 63 - Unsafe Rejoin.pdf`
- `/system/files/decision-document/2025_monaco_grand_prix_-_decision_-_car_22_-_alleged_failing_to_slow_for_yellow_flags.pdf`

Article IDs differ by era too: bare `33.3` (2023–2025) vs section-prefixed
`C3.14.4` (2026+). The parser needs both.

## Seasons available

**2023, 2024, 2025 are complete.** 2026 is mid-flight — the season page lists
15 events but only 1 PDF. Use 2023–2025.

## Mirror

**`TracingInsights/DDocs`** — verified live, pushed 2026-09-22, 3.5GB, 967
commits, GitHub Actions refreshing every 3 hours. Covers 2015, 2018–2026.
Structure `documents/<year>/<event-slug>/<doc-slug>.pdf` plus a per-event
`index.json`:

```json
{"f":"documents\\2025\\monaco-grand-prix\\event-notes-pirelli-preview.pdf",
 "t":"Event Notes - Pirelli Preview","n":1,"p":"21.05.25 12:03"}
```

`p` is publication date, `n` the document number for deduping — both otherwise
requiring a PDF parse. `f` uses Windows backslashes; normalise.

Fetch via `git clone --filter=blob:none --sparse`, or
`raw.githubusercontent.com` (verified HTTP 200).

**Caveats:** **no declared license** (0 stars, personal project) — development
cache only, cite provenance, do not redistribute. No completeness guarantee —
spot-check ~20 docs against fia.com. **Does not mirror regulations.**

## No public dataset exists

Searched Kaggle and HuggingFace: **no dataset of FIA stewards' decisions or
regulations text exists.** All F1 datasets found are Ergast-schema race
results/timing CSVs. This is a genuine gap — worth noting in the write-up as
evidence the project is non-trivial.

Related repos (reference, not corpora): `harningle/fia-doc` (PDF→race-data
parsers, useful parsing reference), `Rouxxel/f1_penalty_predictor`,
`tirthpatell/fia-f1-docs-bot`, `Itsadamdj/f1-docs-agent`.
