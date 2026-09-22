"""Unified retrieval corpus: Regulation Article chunks + Decision chunks,
each given a stable chunk_id and a flattened `text` field for embedding/BM25.

The two source records (regulation_articles.json, decisions.json) have
different shapes (CONTEXT.md) -- this is the one place that reconciles them
into what the retriever needs, without mutating either source file.
"""
import json
import pathlib

PROCESSED_DIR = pathlib.Path("data/processed")


def _regulation_chunk(r: dict, idx: int) -> dict:
    return {
        "chunk_id": f"reg:{r['season']}:{r['kind']}:{r['issue']}:{r['article_id']}",
        "doc_type": "regulation",
        "text": f"Article {r['article_id']} ({r['kind'].title()} Regulations, "
        f"{r['season']}): {r['title']}\n{r['body']}",
        "article_id": r["article_id"],
        "season": r["season"],
        "kind": r["kind"],
        "issue": r["issue"],
        "effective_date": r["effective_date"],
        "source_pdf": r["source_pdf"],
    }


def _decision_chunk(d: dict, idx: int) -> dict:
    parts = [
        f"Decision, {d.get('event')} {d.get('season')}, Document {d.get('document_number')}",
    ]
    if d.get("competitor"):
        parts.append(f"Competitor: {d['competitor']}")
    if d.get("session"):
        parts.append(f"Session: {d['session']}")
    if d.get("fact"):
        parts.append(f"Fact: {d['fact']}")
    if d.get("infringement"):
        parts.append(f"Infringement: {d['infringement']}")
    if d.get("outcome"):
        parts.append(f"Decision: {d['outcome']}")
    if d.get("reason"):
        parts.append(f"Reason: {d['reason']}")
    return {
        "chunk_id": f"dec:{d.get('season')}:{d.get('event')}:{d.get('document_number') or idx}",
        "doc_type": "decision",
        "text": "\n".join(parts),
        "cited_articles": d.get("cited_articles") or [],
        "outcome": d.get("outcome"),
        "season": d.get("season"),
        "event": d.get("event"),
        "source_pdf": d.get("source_pdf"),
    }


def load_corpus() -> list[dict]:
    """Return the full retrieval corpus: every Regulation Article chunk and
    every parsed Decision, each with a chunk_id and a text field."""
    regulations = json.loads((PROCESSED_DIR / "regulation_articles.json").read_text())
    decisions = json.loads((PROCESSED_DIR / "decisions.json").read_text())
    chunks = [_regulation_chunk(r, i) for i, r in enumerate(regulations)]
    chunks += [_decision_chunk(d, i) for i, d in enumerate(decisions)]
    return chunks
