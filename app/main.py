"""Phase 12 (optional): thin FastAPI wrapper around the existing pipeline
stages. Retrieval/rerank/contradiction/generation are already independently
callable (src/index, src/rerank folded into retrieve(), src/contradiction,
src/generate) -- this file only wires them to one HTTP endpoint and serves
the static UI. No new pipeline logic lives here.
"""
import pathlib

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from src.contradiction.detect import detect_contradictions
from src.generate.generate import generate
from src.generate.ollama_gate import MODEL, OllamaUnavailableError
from src.index.retrieve import Retriever

APP_DIR = pathlib.Path(__file__).parent

app = FastAPI(title="F1 Regulations RAG")
app.mount("/static", StaticFiles(directory=APP_DIR / "static"), name="static")

# Built once at process start -- embedding the corpus is the slow part
# (src/index/retrieve.py's own docstring), not per-request work.
_retriever = Retriever()


class AskRequest(BaseModel):
    question: str
    model: str = MODEL


@app.get("/")
def index():
    return FileResponse(APP_DIR / "static" / "index.html")


@app.post("/ask")
def ask(req: AskRequest):
    result = _retriever.retrieve(req.question, top_n=8, use_reranker=True)
    chunks = result["chunks"]
    flags = detect_contradictions(chunks)
    try:
        output = generate(req.question, chunks, flags, model=req.model)
    except OllamaUnavailableError as e:
        return {"error": str(e)}
    return {
        "retrieved_chunk_ids": [c["chunk_id"] for c in chunks],
        "sources": [_source_summary(c) for c in chunks],
        "flags": flags,
        "output": output,
    }


def _source_summary(chunk: dict) -> dict:
    """A display-ready summary for one retrieved chunk -- the frontend
    shows real content, not the raw chunk_id string."""
    if chunk["doc_type"] == "regulation":
        return {
            "chunk_id": chunk["chunk_id"],
            "doc_type": "regulation",
            "label": f"Article {chunk['article_id']}",
            "detail": f"{chunk['kind'].title()} Regulations, {chunk['season']}",
            "excerpt": chunk["text"].split("\n", 1)[-1][:280],
        }
    return {
        "chunk_id": chunk["chunk_id"],
        "doc_type": "decision",
        "label": f"Document {chunk['chunk_id'].rsplit(':', 1)[-1]}",
        "detail": f"{chunk.get('event') or ''} {chunk.get('season') or ''}".strip(),
        "excerpt": (chunk.get("fact") or chunk.get("outcome") or "")[:280],
    }
