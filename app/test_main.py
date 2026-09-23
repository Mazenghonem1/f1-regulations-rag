"""Phase 12 (optional app) check: the API wiring works end-to-end against
the real corpus and a real local Ollama call -- this is not a unit test of
retrieve()/generate() (already covered in src/), just proof the glue holds.

Run: python -m app.test_main
"""
from fastapi.testclient import TestClient

from .main import app


def main():
    client = TestClient(app)

    index = client.get("/")
    assert index.status_code == 200, index.status_code
    assert b"F1 Regulations" in index.content

    ask = client.post("/ask", json={"question": "What is the pit lane speed limit?"})
    assert ask.status_code == 200, ask.status_code
    body = ask.json()
    assert "error" not in body, body
    assert body["retrieved_chunk_ids"], "expected non-empty retrieval"
    assert "answer" in body["output"], body["output"]
    assert body["sources"], "expected non-empty source summaries"
    for s in body["sources"]:
        assert s["doc_type"] in ("regulation", "decision"), s
        assert s["label"] and s["chunk_id"], s

    print("OK — / serves the UI, /ask retrieves + generates a real answer.")


if __name__ == "__main__":
    main()
