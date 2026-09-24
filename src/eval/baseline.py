"""No-retrieval baseline: ask the local LLM the eval questions directly,
with no retrieved context at all, to show retrieval's marginal value on a
domain-specific corpus -- base-model F1-rules knowledge should be visibly
insufficient, especially for Decision-specific and Divergent Precedent
questions no general model could know.
"""
from ..generate.generate import call_ollama
from ..generate.ollama_gate import MODEL, require_ollama

BASELINE_PROMPT_TEMPLATE = """Answer this question about FIA Formula 1 regulations \
or Stewards' Decisions using only your own knowledge. Be concise.

QUESTION: {question}

ANSWER:"""


def run_baseline(questions: list[dict], model: str = MODEL) -> list[dict]:
    """No retrieval, no contradiction detection -- just the raw model
    answering from its own training knowledge. Returns [{question_id,
    question, answer}] for manual/LLM-judge comparison against the
    retrieval-grounded answers."""
    require_ollama(model)
    results = []
    for q in questions:
        prompt = BASELINE_PROMPT_TEMPLATE.format(question=q["question"])
        answer = call_ollama(prompt, model)
        results.append({"question_id": q["id"], "question": q["question"], "answer": answer})
    return results
