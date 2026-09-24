"""Ollama availability gate (PLAN.md): real code, not a comment. No paid-API
fallback anywhere in this project (PROJECT_BRIEF.md) -- if Ollama is absent, stop
loudly and name the exact command to fix it.
"""
import requests

OLLAMA_URL = "http://localhost:11434"
MODEL = "qwen2.5:3b"


class OllamaUnavailableError(RuntimeError):
    pass


def require_ollama(model: str = MODEL) -> None:
    """Raise OllamaUnavailableError naming the exact pull command if Ollama
    isn't running or the model isn't pulled. Call this before any generation
    call -- never fall back to a paid API."""
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=3)
        response.raise_for_status()
    except requests.RequestException as e:
        raise OllamaUnavailableError(
            f"Ollama is not reachable at {OLLAMA_URL}. Install it and run "
            f"`ollama pull {model}` before using generation."
        ) from e

    models = {m["name"] for m in response.json().get("models", [])}
    if model not in models and f"{model}:latest" not in models:
        raise OllamaUnavailableError(
            f"Ollama is running but '{model}' is not pulled. Run "
            f"`ollama pull {model}` before using generation."
        )
