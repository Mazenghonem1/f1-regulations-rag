"""Phase 4 check: a known unchanged Article reports no change; a known
amended one reports a change with a plausible date.

Run: python -m src.chunk.test_article_changes
"""
from .article_changes import diff_issues

ARTICLES = [
    {
        "article_id": "1",
        "title": "STABLE",
        "body": "Nothing changes here across Issues.",
        "season": 2023,
        "kind": "sporting",
        "issue": 1,
        "effective_date": "2022-07-19",
        "source_pdf": "issue1.pdf",
    },
    {
        "article_id": "1",
        "title": "STABLE",
        # Re-wrapped line only -- same wording, different pdftotext line width.
        "body": "Nothing\nchanges here\nacross Issues.",
        "season": 2023,
        "kind": "sporting",
        "issue": 2,
        "effective_date": "2022-10-19",
        "source_pdf": "issue2.pdf",
    },
    {
        "article_id": "2",
        "title": "AMENDED",
        "body": "The penalty is a reprimand.",
        "season": 2023,
        "kind": "sporting",
        "issue": 1,
        "effective_date": "2022-07-19",
        "source_pdf": "issue1.pdf",
    },
    {
        "article_id": "2",
        "title": "AMENDED",
        "body": "The penalty is a ten-second time penalty.",
        "season": 2023,
        "kind": "sporting",
        "issue": 2,
        "effective_date": "2022-10-19",
        "source_pdf": "issue2.pdf",
    },
]

changes = diff_issues(ARTICLES)

# unchanged Article (whitespace-only rewrap doesn't count as a change)
assert changes.get("1", []) == [], changes.get("1")

# amended Article reports a change with the later Issue's effective date
assert len(changes["2"]) == 1
change = changes["2"][0]
assert change["from_issue"] == 1 and change["to_issue"] == 2
assert change["changed_on"] == "2022-10-19"
assert change["change_summary"] == "text changed"

print("OK — unchanged Article reports nothing, amended Article reports a dated change.")
