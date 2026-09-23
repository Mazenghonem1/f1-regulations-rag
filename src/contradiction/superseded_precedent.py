"""Superseded Precedent detector (CONTEXT.md): a Decision applying an
Article that was later amended, so the Decision no longer reflects the
current rule. Not a disagreement -- a timeline problem, using the Article's
actual change date from article_changes.json (Phase 4), not a heuristic.
"""
from .article_ids import top_level_article


def detect_superseded_precedent(decisions: list[dict], article_changes: dict) -> list[dict]:
    """`decisions` are Decision-type chunks with a `date` (ISO "YYYY-MM-DD")
    and `cited_articles`. `article_changes` is the Phase 4 table: article_id
    -> [{changed_on, from_issue, to_issue, change_summary, ...}], keyed by
    top-level Article ID.

    Flags a Decision against an Article change with changed_on strictly
    after the Decision's date -- the Decision predates a later amendment.
    A Decision's cited sub-clause (e.g. "33.3") is normalised to its
    top-level Article ("33") for the change lookup, but the flag reports
    the original cited ID. `match_granularity` is "exact" when the citation
    was already a bare Article that matched directly, or "article" when it
    came via sub-clause normalisation -- an Article-level change does not
    prove the specific sub-clause changed, so this is a real precision
    cost, not just bookkeeping.

    A Decision with no parsed date, a citation with no corpus counterpart
    (e.g. Appendix L / ISC), or an Article with no recorded changes,
    contributes no flags rather than raising."""
    flags = []
    for d in decisions:
        decision_date = d.get("date")
        if not decision_date:
            continue
        for article in d.get("cited_articles") or []:
            top_level = top_level_article(article)
            if top_level is None:
                continue
            granularity = "exact" if top_level == article else "article"
            for change in article_changes.get(top_level, []):
                if change["changed_on"] > decision_date:
                    flags.append(
                        {
                            "type": "superseded_precedent",
                            "article": article,
                            "match_granularity": granularity,
                            "decision": d["chunk_id"],
                            "decision_date": decision_date,
                            "changed_on": change["changed_on"],
                            "change_summary": change["change_summary"],
                            "from_issue": change["from_issue"],
                            "to_issue": change["to_issue"],
                        }
                    )
    return flags
