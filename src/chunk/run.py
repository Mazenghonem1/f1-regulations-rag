"""Chunking orchestrator: data/raw/ -> data/processed/ chunks + coverage report.

Run: python -m src.chunk.run
"""
import json
import pathlib

from ..contradiction.article_ids import top_level_article
from .article_changes import diff_issues, latest_versions
from .decisions import parse_decision
from .dedupe import dedupe_decisions
from .extract import extract_text
from .reg_filenames import parse_filename
from .regulations import split_articles

RAW_DIR = pathlib.Path("data/raw")
PROCESSED_DIR = pathlib.Path("data/processed")
RESULTS_DIR = pathlib.Path("results")

DECISION_FIELDS = ["cited_articles", "outcome", "date"]  # coverage is reported on these


def _load_sidecar(pdf_path: pathlib.Path) -> dict:
    sidecar = pdf_path.with_suffix(pdf_path.suffix + ".json")
    return json.loads(sidecar.read_text()) if sidecar.exists() else {}


def process_decisions() -> tuple[list[dict], dict]:
    records = []
    for pdf_path in sorted((RAW_DIR / "decisions").rglob("*.pdf")):
        meta = _load_sidecar(pdf_path)
        if meta.get("doc_type") != "decision":
            continue
        text = extract_text(pdf_path)
        record = parse_decision(
            text,
            {
                "season": meta.get("season"),
                "event": meta.get("event"),
                "source_pdf": str(pdf_path),
            },
        )
        records.append(record)

    kept, dropped = dedupe_decisions(records)
    # Right of Review / Protest / Summons documents are real Decisions but
    # not the fixed-label per-incident template (see parse_decision) -- the
    # >90% coverage bar is about that template, so it's measured only over
    # the subset that could plausibly carry the labels.
    templated = [r for r in kept if r["is_incident_template"]]
    non_templated = [r for r in kept if not r["is_incident_template"]]

    coverage = {
        "total_candidates": len(records),
        "deduped_count": len(dropped),
        "kept_count": len(kept),
        "templated_count": len(templated),
        "non_templated_count": len(non_templated),
        "field_coverage": {},
        "failures": {},
    }
    for field in DECISION_FIELDS:
        present = [r for r in templated if r.get(field)]
        coverage["field_coverage"][field] = {
            "present": len(present),
            "total": len(templated),
            "rate": round(len(present) / len(templated), 3) if templated else 0.0,
        }
        coverage["failures"][field] = [
            r["source_pdf"] for r in templated if not r.get(field)
        ]
    both = [r for r in templated if r.get("cited_articles") and r.get("outcome")]
    coverage["both_article_and_outcome"] = {
        "present": len(both),
        "total": len(templated),
        "rate": round(len(both) / len(templated), 3) if templated else 0.0,
    }

    cited = {a for r in templated for a in r.get("cited_articles") or []}
    isc = {a for a in cited if top_level_article(a) is None}
    coverage["citation_corpus_coverage"] = {
        "distinct_cited_articles": len(cited),
        "isc_no_corpus_counterpart": len(isc),
        "isc_examples": sorted(isc)[:5],
        "normalisable_to_top_level_article": len(cited) - len(isc),
    }
    return kept, coverage


def process_regulations() -> list[dict]:
    chunks = []
    for pdf_path in sorted((RAW_DIR / "regulations").glob("*.pdf")):
        meta = _load_sidecar(pdf_path)
        if meta.get("doc_type") != "regulation":
            continue
        name_meta = parse_filename(pdf_path.name)
        if name_meta["season"] not in (2023, 2024, 2025):
            continue
        text = extract_text(pdf_path)
        for article in split_articles(text):
            chunks.append(
                {
                    **article,
                    **name_meta,
                    "source_pdf": str(pdf_path),
                }
            )
    return chunks


def main():
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    decisions, coverage = process_decisions()
    (PROCESSED_DIR / "decisions.json").write_text(json.dumps(decisions, indent=2))

    regulations = latest_versions(process_regulations())
    (PROCESSED_DIR / "regulation_articles.json").write_text(
        json.dumps(regulations, indent=2)
    )

    changes = diff_issues(regulations)
    (PROCESSED_DIR / "article_changes.json").write_text(json.dumps(changes, indent=2))

    (RESULTS_DIR / "parse_coverage.json").write_text(json.dumps(coverage, indent=2))

    print(f"Decisions: {len(decisions)} kept ({coverage['deduped_count']} deduped)")
    for field, stats in coverage["field_coverage"].items():
        print(f"  {field}: {stats['present']}/{stats['total']} ({stats['rate']:.1%})")
    both = coverage["both_article_and_outcome"]
    print(f"  both article+outcome: {both['present']}/{both['total']} ({both['rate']:.1%})")
    print(f"Regulation Articles: {len(regulations)} chunks")
    print(f"Article changes: {len(changes)} Articles with recorded changes")


if __name__ == "__main__":
    main()
