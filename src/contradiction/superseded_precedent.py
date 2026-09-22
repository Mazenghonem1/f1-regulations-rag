"""Superseded Precedent detector (CONTEXT.md): a Decision applying an
Article that was later amended, so the Decision no longer reflects the
current rule. Not a disagreement -- a timeline problem, using the Article's
actual change date from article_changes.json (Phase 4), not a heuristic.
"""


def detect_superseded_precedent(decisions: list[dict], article_changes: dict) -> list[dict]:
    """`decisions` are Decision-type chunks with a `date` (ISO "YYYY-MM-DD")
    and `cited_articles`. `article_changes` is the Phase 4 table: article_id
    -> [{changed_on, from_issue, to_issue, change_summary, ...}].

    Flags a Decision against an Article change with changed_on strictly
    after the Decision's date -- the Decision predates a later amendment.
    A Decision with no parsed date, or an Article with no recorded changes,
    contributes no flags rather than raising."""
    flags = []
    for d in decisions:
        decision_date = d.get("date")
        if not decision_date:
            continue
        for article in d.get("cited_articles") or []:
            for change in article_changes.get(article, []):
                if change["changed_on"] > decision_date:
                    flags.append(
                        {
                            "type": "superseded_precedent",
                            "article": article,
                            "decision": d["chunk_id"],
                            "decision_date": decision_date,
                            "changed_on": change["changed_on"],
                            "change_summary": change["change_summary"],
                            "from_issue": change["from_issue"],
                            "to_issue": change["to_issue"],
                        }
                    )
    return flags
