"""Check: the Ollama gate raises with a useful message when the
service is down; the JSON parser handles a known-malformed response.

Run: python -m src.generate.test_generate
"""
from .ollama_gate import OllamaUnavailableError, require_ollama
from .parse_output import MalformedOutputError, parse_structured_output

# the gate raises a useful error when Ollama is unreachable (nothing is
# listening on this port in the test environment's default case; if Ollama
# happens to be running with the model pulled, skip this half)
try:
    require_ollama(model="__definitely-not-a-real-pulled-model__")
    print("(skipped: a model matching the bogus name was somehow found)")
except OllamaUnavailableError as e:
    assert "ollama pull" in str(e), e

# well-formed JSON, possibly wrapped in markdown fences and prose -- parses
WRAPPED = """Here is the answer:
```json
{"answer": "No further action was appropriate.", "citations": [{"doc_id": "dec:1", "article_or_decision": "33.3", "quote_or_paraphrase": "left the track without justifiable reason"}], "contradictions_flagged": []}
```
"""
parsed = parse_structured_output(WRAPPED)
assert parsed["answer"] == "No further action was appropriate."
assert parsed["citations"][0]["doc_id"] == "dec:1"

# known-malformed output (truncated JSON) raises MalformedOutputError
TRUNCATED = '{"answer": "Partial response with no closing'
try:
    parse_structured_output(TRUNCATED)
    assert False, "expected MalformedOutputError"
except MalformedOutputError:
    pass

# well-formed JSON missing a required key also raises
MISSING_KEY = '{"answer": "ok", "citations": []}'
try:
    parse_structured_output(MISSING_KEY)
    assert False, "expected MalformedOutputError"
except MalformedOutputError:
    pass

print(
    "OK — Ollama gate raises a useful error when unavailable; "
    "JSON parser tolerates wrapping and rejects malformed/incomplete output."
)
