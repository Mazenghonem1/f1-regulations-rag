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


def _call_ollama(prompt: str, model: str) -> str:
    response = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={"model": model, "prompt": prompt, "stream": False},
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
        raw = _call_ollama(prompt, model)
        try:
            return parse_structured_output(raw)
        except MalformedOutputError as e:
            last_error = e
    raise last_error
