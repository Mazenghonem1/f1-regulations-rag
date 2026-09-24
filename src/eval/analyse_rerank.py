"""Root-cause the reranker regression (Precision@8: 0.654 -> 0.615,
17/26 -> 16/26 on results/eval_qwen2.5_3b_full_20260923T031322_precision_detail.json).

precision_at_k never persists pre/post rerank orderings, so this re-runs
retrieval for just the 7 known-flipped questions (deterministic given a
fixed corpus and query) to get the evidence log_query would have written.

Run: python -m src.eval.analyse_rerank
"""
import json
import pathlib

from ..index.retrieve import Retriever

EVAL_SET_PATH = pathlib.Path("data/eval_set.json")
RESULTS_DIR = pathlib.Path("results")

IMPROVED = ["q04", "q13", "q27"]
REGRESSED = ["q14", "q19", "q20", "q30"]


def _rank(order: list[str], chunk_id: str) -> int | None:
    return order.index(chunk_id) + 1 if chunk_id in order else None


def analyse() -> list[dict]:
    questions = {q["id"]: q for q in json.loads(EVAL_SET_PATH.read_text())}
    retriever = Retriever()
    rows = []
    for qid in IMPROVED + REGRESSED:
        q = questions[qid]
        gold_ids = q.get("gold_chunk_ids") or []
        result = retriever.retrieve(q["question"], top_n=8, use_reranker=True)
        pre, post = result["pre_rerank_order"], result["post_rerank_order"]
        for gold in gold_ids:
            pre_rank = _rank(pre, gold)
            post_rank = _rank(post, gold)
            displacers = [cid for cid in post[: (pre_rank or 8)] if cid != gold] if pre_rank else []
            row = {
                "id": qid,
                "direction": "improved" if qid in IMPROVED else "regressed",
                "question": q["question"],
                "gold_chunk_id": gold,
                "pre_rerank_rank": pre_rank,
                "post_rerank_rank": post_rank,
                "displaced_by": displacers[:3],
            }
            rows.append(row)
    return rows


def format_report(rows: list[dict]) -> str:
    lines = ["# Reranker regression analysis\n"]
    for row in rows:
        lines.append(f"## {row['id']} ({row['direction']}) — {row['question']}")
        lines.append(f"- gold: `{row['gold_chunk_id']}`")
        lines.append(f"- pre-rerank rank: {row['pre_rerank_rank']}, post-rerank rank: {row['post_rerank_rank']}")
        if row["displaced_by"]:
            lines.append(f"- displaced by (post-rerank, ahead of gold): {row['displaced_by']}")
        lines.append("")
    return "\n".join(lines)


def main():
    rows = analyse()
    flipped_ids = {r["id"] for r in rows}
    assert flipped_ids == set(IMPROVED + REGRESSED), flipped_ids

    for row in rows:
        print(
            f"{row['id']:5s} {row['direction']:9s} gold={row['gold_chunk_id']:35s} "
            f"pre={row['pre_rerank_rank']} post={row['post_rerank_rank']} "
            f"displaced_by={row['displaced_by']}"
        )

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / "rerank_analysis_detail.json").write_text(json.dumps(rows, indent=2))
    print(f"\nWrote {len(rows)} rows -> results/rerank_analysis_detail.json")


if __name__ == "__main__":
    main()
