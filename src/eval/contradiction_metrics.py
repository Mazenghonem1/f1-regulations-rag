"""Contradiction recall and precision, reported per detector (ADR 0002) --
the headline metric. Recall: of the seeded_contradiction questions, what
fraction did the system flag (unsuppressed) for the right Article. Precision:
of the negative_justified_distinction questions, what fraction did the
system correctly NOT flag.
"""
from ..contradiction.detect import detect_contradictions


def _flagged_for_article(flags: list[dict], article: str, detector: str) -> bool:
    for f in flags:
        if f.get("suppressed"):
            continue
        if f["type"] != detector:
            continue
        if detector == "divergent_precedent" and f["article"] == article:
            return True
        if detector == "superseded_precedent" and f["article"] == article:
            return True
    return False


def contradiction_metrics(retriever, questions: list[dict], article_changes: dict) -> dict:
    """Returns per-detector {recall, precision, tp, fn, tn, fp} plus an
    overall summary. Only questions with a `detector` field are scored
    (seeded_contradiction and negative_justified_distinction types)."""
    by_detector: dict[str, dict[str, int]] = {}

    for q in questions:
        detector = q.get("detector")
        if not detector:
            continue
        by_detector.setdefault(detector, {"tp": 0, "fn": 0, "tn": 0, "fp": 0})

        result = retriever.retrieve(q["question"], top_n=8, use_reranker=True)
        flags = detect_contradictions(result["chunks"], article_changes)
        flagged = _flagged_for_article(flags, q["gold_article"], detector)

        expected = q["expected_flag"]
        counts = by_detector[detector]
        if expected and flagged:
            counts["tp"] += 1
        elif expected and not flagged:
            counts["fn"] += 1
        elif not expected and not flagged:
            counts["tn"] += 1
        else:
            counts["fp"] += 1

    summary = {}
    for detector, counts in by_detector.items():
        tp, fn, tn, fp = counts["tp"], counts["fn"], counts["tn"], counts["fp"]
        recall = tp / (tp + fn) if (tp + fn) else None
        precision = tp / (tp + fp) if (tp + fp) else None
        summary[detector] = {**counts, "recall": recall, "precision": precision}
    return summary
