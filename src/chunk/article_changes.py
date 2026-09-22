"""Phase 4: diff consecutive Regulation Issues per Article.

Ground truth for Superseded Precedent (CONTEXT.md) -- a Decision applying an
Article that was later amended. Built from real Issue diffs, not heuristics
(PLAN.md).

2023-2025 regulations use bare Article IDs only (no section-prefixed 2026+
notation was scraped -- docs/RECON.md), so there is no cross-notation
boundary to normalise here. An Article ID is tracked as the same Article
across (season, kind) as long as its ID string is unchanged; a season
rollover is a new Issue sequence like any other, since Issue N+1 supersedes
Issue N regardless of season boundary (CONTEXT.md).
"""
import json
import pathlib
import re
from collections import defaultdict

PROCESSED_DIR = pathlib.Path("data/processed")

_WS_RE = re.compile(r"\s+")


def _normalised(body: str) -> str:
    """Collapse whitespace before comparing bodies -- pdftotext rewraps lines
    at a different width between Issues even when the wording is identical,
    which would otherwise register as a false "text changed" on nearly every
    Article, every Issue (verified: Article 33 issue-2->3 differs only in
    line-wrap)."""
    return _WS_RE.sub(" ", body).strip()


def _latest_versions(articles: list[dict]) -> list[dict]:
    """Some Issues were re-published same-day under a new source PDF (e.g.
    "..._v1.pdf" / "..._v2.pdf", or a "-v2" reissue with no "-v1" on disk) --
    same (season, kind, issue), two source_pdf values. Keep only the
    lexicographically-last source_pdf's articles per (season, kind, issue),
    since "_v2" > "_v1" and a bare filename (the v1-equivalent, when no v1
    file exists) sorts before any "-v2" suffix."""
    by_key: dict[tuple, str] = {}
    for a in articles:
        key = (a["season"], a["kind"], a["issue"])
        if key not in by_key or a["source_pdf"] > by_key[key]:
            by_key[key] = a["source_pdf"]
    keep_pdfs = set(by_key.values())
    return [a for a in articles if a["source_pdf"] in keep_pdfs]


def _issue_sequence(articles: list[dict]) -> dict[tuple, dict[int, dict]]:
    """(season, kind) -> {issue: {article_id: article}}."""
    by_family: dict[tuple, dict[int, dict]] = defaultdict(dict)
    for a in articles:
        family = (a["season"], a["kind"])
        by_family[family].setdefault(a["issue"], {})[a["article_id"]] = a
    return by_family


def diff_issues(articles: list[dict]) -> dict[str, list[dict]]:
    """Return {article_id: [{changed_on, from_issue, to_issue, change_summary}, ...]}
    across every (season, kind) family's consecutive Issues, in chronological
    order. An Article absent from an Issue and present in the next is an
    addition; present then absent is a removal; present in both with a
    different body is a text change."""
    articles = _latest_versions(articles)
    by_family = _issue_sequence(articles)

    changes: dict[str, list[dict]] = defaultdict(list)
    for (season, kind), issues in by_family.items():
        ordered_issue_nums = sorted(issues)
        for prev_n, next_n in zip(ordered_issue_nums, ordered_issue_nums[1:]):
            prev_articles = issues[prev_n]
            next_articles = issues[next_n]
            changed_on = next(iter(next_articles.values()))["effective_date"]
            ids = set(prev_articles) | set(next_articles)
            for aid in ids:
                prev = prev_articles.get(aid)
                nxt = next_articles.get(aid)
                if prev is None:
                    summary = "added"
                elif nxt is None:
                    summary = "removed"
                elif _normalised(prev["body"]) != _normalised(nxt["body"]):
                    summary = "text changed"
                else:
                    continue
                changes[aid].append(
                    {
                        "season": season,
                        "kind": kind,
                        "changed_on": changed_on,
                        "from_issue": prev_n,
                        "to_issue": next_n,
                        "change_summary": summary,
                    }
                )
    for aid in changes:
        changes[aid].sort(key=lambda c: (c["season"], c["from_issue"]))
    return dict(changes)


def main():
    articles = json.loads((PROCESSED_DIR / "regulation_articles.json").read_text())
    changes = diff_issues(articles)
    (PROCESSED_DIR / "article_changes.json").write_text(json.dumps(changes, indent=2))
    print(f"Article change history: {len(changes)} Articles with recorded changes")
    print(f"  total change events: {sum(len(v) for v in changes.values())}")


if __name__ == "__main__":
    main()
