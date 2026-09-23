"""Phase 8 orchestrator: run the full eval set through retrieval (with and
without reranking), contradiction detection, generation, and the
no-retrieval baseline, computing all four metrics and logging every run to
results/ (PLAN.md's "reproducibility is the point").

Run: python -m src.eval.run_eval [--smoke] [--model qwen2.5:3b]
"""
import argparse
import json
import pathlib
import time

from ..contradiction.detect import detect_contradictions
from ..generate.generate import generate
from ..index.retrieve import Retriever
from .baseline import run_baseline
from .contradiction_metrics import contradiction_metrics
from .faithfulness import citation_faithfulness
from .precision_at_k import precision_at_k

EVAL_SET_PATH = pathlib.Path("data/eval_set.json")
PROCESSED_DIR = pathlib.Path("data/processed")
RESULTS_DIR = pathlib.Path("results")


def load_eval_set(smoke: bool = False) -> list[dict]:
    questions = json.loads(EVAL_SET_PATH.read_text())
    return questions[:3] if smoke else questions


def run_generation(retriever, questions: list[dict], article_changes: dict, model: str) -> list[dict]:
    outputs = []
    for q in questions:
        result = retriever.retrieve(q["question"], top_n=8, use_reranker=True)
        chunks = result["chunks"]
        flags = detect_contradictions(chunks, article_changes)
        try:
            output = generate(q["question"], chunks, flags, model=model)
        except Exception as e:
            output = {"error": str(e)}
        outputs.append(
            {
                "question_id": q["id"],
                "retrieved_chunk_ids": [c["chunk_id"] for c in chunks],
                "flags": flags,
                "output": output,
            }
        )
    return outputs


def run_eval(smoke: bool = False, model: str = "qwen2.5:3b") -> dict:
    questions = load_eval_set(smoke)
    article_changes = json.loads((PROCESSED_DIR / "article_changes.json").read_text())

    retriever = Retriever()
    chunks_by_id = retriever.by_id

    precision_no_rerank = precision_at_k(retriever, questions, k=8, use_reranker=False)
    precision_with_rerank = precision_at_k(retriever, questions, k=8, use_reranker=True)

    contradiction_scores = contradiction_metrics(retriever, questions, article_changes)

    generation_outputs = run_generation(retriever, questions, article_changes, model)
    valid_outputs = [
        {"question_id": o["question_id"], "output": o["output"]}
        for o in generation_outputs
        if "error" not in o["output"]
    ]
    faithfulness = citation_faithfulness(valid_outputs, chunks_by_id, model=model)

    baseline_results = run_baseline(questions, model=model)

    summary = {
        "model": model,
        "smoke": smoke,
        "num_questions": len(questions),
        "retrieval_precision_at_8": {
            "without_reranking": precision_no_rerank["precision"],
            "with_reranking": precision_with_rerank["precision"],
            "scored": precision_with_rerank["scored"],
            "skipped_no_gold": precision_with_rerank["skipped"],
        },
        "contradiction_metrics": contradiction_scores,
        "citation_faithfulness": {
            "score": faithfulness["faithfulness"],
            "scored": faithfulness["scored"],
            "unsupported": faithfulness["unsupported"],
        },
        "generation_errors": sum(1 for o in generation_outputs if "error" in o["output"]),
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%dT%H%M%S")
    run_name = f"eval_{model.replace(':', '_')}_{'smoke' if smoke else 'full'}_{timestamp}"

    (RESULTS_DIR / f"{run_name}_summary.json").write_text(json.dumps(summary, indent=2))
    (RESULTS_DIR / f"{run_name}_precision_detail.json").write_text(
        json.dumps(
            {"without_reranking": precision_no_rerank, "with_reranking": precision_with_rerank},
            indent=2,
        )
    )
    (RESULTS_DIR / f"{run_name}_generation.json").write_text(json.dumps(generation_outputs, indent=2))
    (RESULTS_DIR / f"{run_name}_faithfulness.json").write_text(json.dumps(faithfulness, indent=2))
    (RESULTS_DIR / f"{run_name}_baseline.json").write_text(json.dumps(baseline_results, indent=2))

    print(json.dumps(summary, indent=2))
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true", help="run only the first 3 questions")
    parser.add_argument("--model", default="qwen2.5:3b")
    args = parser.parse_args()
    run_eval(smoke=args.smoke, model=args.model)
