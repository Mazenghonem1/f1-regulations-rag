"""Citation faithfulness: does a generated citation's quote_or_paraphrase
actually appear in / get supported by the chunk it cites. Scored with the
local LLM as judge (PROJECT_BRIEF.md -- no paid judge model), against a plain
yes/no rubric per citation. Known limitation, stated plainly: qwen2.5
judging its own family's output is not GPT-4-class evaluation (PLAN.md).
"""
from ..generate.generate import call_ollama
from ..generate.ollama_gate import MODEL, require_ollama

JUDGE_PROMPT_TEMPLATE = """You are a strict fact-checker. Given a source passage and a claimed citation, answer ONLY "yes" or "no": does the source passage support the claimed citation?

SOURCE PASSAGE:
{source}

CLAIMED CITATION:
{claim}

Answer with exactly one word, "yes" or "no":"""


def judge_citation(source_text: str, claim: str, model: str = MODEL) -> bool:
    """True if the local LLM judges `claim` as supported by `source_text`."""
    prompt = JUDGE_PROMPT_TEMPLATE.format(source=source_text, claim=claim)
    raw = call_ollama(prompt, model).strip().lower()
    return raw.startswith("yes")


def citation_faithfulness(
    generated_outputs: list[dict], chunks_by_id: dict[str, dict], model: str = MODEL
) -> dict:
    """`generated_outputs` is a list of {question_id, output} where `output`
    is the parsed structured JSON from generate(). Scores every citation
    across every output against the chunk it names. Returns {faithfulness,
    scored, unsupported, per_citation}."""
    require_ollama(model)
    results = []
    for entry in generated_outputs:
        for citation in entry["output"].get("citations", []):
            chunk = chunks_by_id.get(citation.get("doc_id"))
            if chunk is None:
                results.append(
                    {
                        "question_id": entry["question_id"],
                        "doc_id": citation.get("doc_id"),
                        "supported": False,
                        "reason": "doc_id not found in retrieved chunks",
                    }
                )
                continue
            claim = citation.get("quote_or_paraphrase", "")
            supported = judge_citation(chunk["text"], claim, model)
            results.append(
                {
                    "question_id": entry["question_id"],
                    "doc_id": citation["doc_id"],
                    "supported": supported,
                }
            )

    scored = len(results)
    faithful = sum(r["supported"] for r in results)
    return {
        "faithfulness": faithful / scored if scored else None,
        "scored": scored,
        "unsupported": scored - faithful,
        "per_citation": results,
    }
