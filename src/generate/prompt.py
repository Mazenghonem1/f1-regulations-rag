"""Prompt construction: answer only from retrieved context, no outside
knowledge, structured JSON output with citations and contradiction flags.
Contradiction flags are passed in explicitly so the model must surface them
rather than silently pick a source (CONTEXT.md's whole point).
"""
SYSTEM_PROMPT = """You are an assistant answering questions about FIA Formula 1 \
regulations and Stewards' Decisions. Answer ONLY using the retrieved context \
provided below -- do not use any outside knowledge of F1 rules or events.

You MUST include at least one entry in "citations" for every context chunk \
your answer draws on. Never leave "citations" empty if the context contains \
anything relevant -- copy the exact [chunk_id] shown before each context \
entry into "doc_id". An answer with no citations is treated as invalid.

If contradiction flags are listed, you MUST mention them explicitly in your \
answer and express appropriate uncertainty. Do not silently pick one source \
and ignore the conflict.

Respond with ONLY a JSON object matching this exact shape, no other text:
{
  "answer": "<your answer, in prose>",
  "citations": [
    {"doc_id": "<the exact chunk_id from context, e.g. dec:2023:Austrian Grand Prix:66>", "article_or_decision": "<Article number or Decision reference>", "quote_or_paraphrase": "<short quote or paraphrase supporting the answer>"}
  ],
  "contradictions_flagged": [
    "<one string per contradiction flag surfaced to the user, or empty list if none>"
  ]
}

Example citations entry: {"doc_id": "reg:2023:sporting:1:33", "article_or_decision": "Article 33", "quote_or_paraphrase": "drivers may not leave the track without a justifiable reason"}"""


def _format_chunk(chunk: dict) -> str:
    label = chunk.get("article_id") or chunk.get("chunk_id")
    return f"[{chunk['chunk_id']}] ({chunk['doc_type']}, {label})\n{chunk['text']}"


def _format_flag(flag: dict) -> str:
    if flag["type"] == "divergent_precedent":
        return (
            f"DIVERGENT PRECEDENT on Article {flag['article']}: Decisions "
            f"{flag['decisions']} cite the same Article on a similar incident "
            f"but reached different outcomes: {flag['outcomes']}."
        )
    return (
        f"SUPERSEDED PRECEDENT: Decision {flag['decision']} ({flag['decision_date']}) "
        f"cites Article {flag['article']}, which was amended on {flag['changed_on']} "
        f"(Issue {flag['from_issue']} -> {flag['to_issue']}), after the Decision."
    )


def build_prompt(query: str, chunks: list[dict], flags: list[dict]) -> str:
    """`chunks` is the final retrieved/reranked chunk list; `flags` is the
    unsuppressed contradiction flags for those chunks (suppressed flags are
    not the model's concern -- they were already ruled out as false
    positives)."""
    context = "\n\n".join(_format_chunk(c) for c in chunks)
    unsuppressed = [f for f in flags if not f.get("suppressed", False)]
    flags_text = (
        "\n".join(_format_flag(f) for f in unsuppressed)
        if unsuppressed
        else "None."
    )
    return (
        f"{SYSTEM_PROMPT}\n\n"
        f"CONTEXT:\n{context}\n\n"
        f"CONTRADICTION FLAGS:\n{flags_text}\n\n"
        f"QUESTION: {query}"
    )
