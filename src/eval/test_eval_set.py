"""Check: every question's gold_chunk_ids actually exist in the corpus
(a real bug hit exactly this once: a chunk id that didn't exist).

Run: python -m src.eval.test_eval_set
"""
import json
import pathlib

from ..index.corpus import load_corpus

EVAL_SET_PATH = pathlib.Path("data/eval_set.json")


def main():
    questions = json.loads(EVAL_SET_PATH.read_text())
    chunk_ids = {c["chunk_id"] for c in load_corpus()}

    missing = [
        (q["id"], gid)
        for q in questions
        for gid in q.get("gold_chunk_ids") or []
        if gid not in chunk_ids
    ]
    assert not missing, f"gold_chunk_ids not in corpus: {missing}"

    ids = [q["id"] for q in questions]
    assert len(ids) == len(set(ids)), "duplicate question ids"

    print(f"OK — {len(questions)} questions, all gold_chunk_ids exist in the corpus.")


if __name__ == "__main__":
    main()
