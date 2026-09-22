"""Phase 6 orchestrator: run both named detectors over a retrieved chunk
set and log every flag to results/ (PLAN.md's "log everything" rule).
"""
import json
import pathlib

from .divergent_precedent import detect_divergent_precedent
from .superseded_precedent import detect_superseded_precedent

RESULTS_DIR = pathlib.Path("results")
PROCESSED_DIR = pathlib.Path("data/processed")


def detect_contradictions(chunks: list[dict], article_changes: dict | None = None) -> list[dict]:
    """`chunks` is a retrieved/reranked chunk list (mixed doc_type). Runs
    both detectors over the Decision-type subset and returns the combined
    flag list, unsuppressed flags first."""
    if article_changes is None:
        article_changes = json.loads((PROCESSED_DIR / "article_changes.json").read_text())
    decisions = [c for c in chunks if c.get("doc_type") == "decision"]

    flags = detect_divergent_precedent(decisions)
    flags += detect_superseded_precedent(decisions, article_changes)
    flags.sort(key=lambda f: f["suppressed"] if f["type"] == "divergent_precedent" else False)
    return flags


def log_flags(query: str, flags: list[dict], run_name: str = "manual") -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    entry = {"run": run_name, "query": query, "flags": flags}
    with (RESULTS_DIR / "contradiction_log.jsonl").open("a") as f:
        f.write(json.dumps(entry) + "\n")
