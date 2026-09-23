"""Phase 7 entrypoint: citation-grounded structured generation via local
Ollama. Retrieval/rerank/contradiction stages are already independently
callable (Phases 5-6) -- this module only adds the generation step, gated
on Ollama being present (no paid-API fallback, CLAUDE.md).
"""
import requests

from .ollama_gate import MODEL, OLLAMA_URL, require_ollama
from .parse_output import MalformedOutputError, parse_structured_output
from .prompt import build_prompt


# CPU-only Intel Mac: qwen2.5:3b runs ~8-12 tok/s (docs/RECON.md), and a
# structured JSON answer with several citations and contradiction flags
# easily runs to a few hundred tokens -- 180s was too tight and timed out
# on a real query with 12 flags (verified).
GENERATE_TIMEOUT_S = 600


# The exact response shape (PLAN.md): {answer, citations: [{doc_id,
# article_or_decision, quote_or_paraphrase}], contradictions_flagged}.
# Passed to Ollama as a JSON Schema (not just format="json") so the required
# keys are grammar-constrained at decode time, not merely requested in text.
# Verified necessary: format="json" alone produced syntactically valid JSON
# that invented its own shape ({"answer": ..., "reasoning": ...}) instead of
# the required keys, on the same question that a plain-text-only instruction
# had earlier caused to be answered in prose -- a schema-shaped 3B model
# failure that neither a retry count nor a "respond with ONLY JSON" sentence
# fixes, only decode-time constraint does.
RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "answer": {"type": "string"},
        "citations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "doc_id": {"type": "string"},
                    "article_or_decision": {"type": "string"},
                    "quote_or_paraphrase": {"type": "string"},
                },
                "required": ["doc_id", "article_or_decision", "quote_or_paraphrase"],
            },
        },
        "contradictions_flagged": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["answer", "citations", "contradictions_flagged"],
}


def call_ollama(prompt: str, model: str, response_format=None) -> str:
    payload = {"model": model, "prompt": prompt, "stream": False}
    if response_format is not None:
        payload["format"] = response_format
    response = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json=payload,
        timeout=GENERATE_TIMEOUT_S,
    )
    response.raise_for_status()
    return response.json()["response"]


def generate(
    query: str, chunks: list[dict], flags: list[dict], model: str = MODEL
) -> dict:
    """Answer `query` from `chunks` (the retrieved/reranked context) and
    `flags` (contradiction flags, unsuppressed ones surfaced explicitly).
    Gates on Ollama being reachable with `model` pulled; retries the
    generation once on malformed JSON, then raises rather than silently
    dropping a flag (PLAN.md)."""
    require_ollama(model)
    prompt = build_prompt(query, chunks, flags)

    last_error = None
    for _attempt in range(2):
        raw = call_ollama(prompt, model, response_format=RESPONSE_SCHEMA)
        try:
            return parse_structured_output(raw)
        except MalformedOutputError as e:
            last_error = e
    raise last_error
