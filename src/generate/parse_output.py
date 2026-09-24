"""Defensive parsing of the LLM's structured JSON output. A 3B model will
occasionally wrap the JSON in prose or markdown fences -- extract and parse
defensively rather than requiring exact output.
"""
import json
import re

REQUIRED_KEYS = {"answer", "citations", "contradictions_flagged"}

_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


class MalformedOutputError(ValueError):
    pass


def parse_structured_output(raw: str) -> dict:
    """Extract and parse the model's JSON object from raw text, tolerating
    markdown code fences or leading/trailing prose around it. Raises
    MalformedOutputError if no valid, complete object can be recovered --
    the caller retries once, then fails loudly rather than silently
    dropping a flag."""
    match = _JSON_OBJECT_RE.search(raw)
    if not match:
        raise MalformedOutputError(f"No JSON object found in output: {raw!r}")

    try:
        parsed = json.loads(match.group(0))
    except json.JSONDecodeError as e:
        raise MalformedOutputError(f"Invalid JSON in output: {e}") from e

    missing = REQUIRED_KEYS - parsed.keys()
    if missing:
        raise MalformedOutputError(f"Output missing required keys: {missing}")

    return parsed
