"""Phase 6 check: two Decisions, same Article, different Outcomes -> flagged;
the same pair with a Mitigating Factor present -> not flagged; a Decision
predating an Article change -> superseded.

Run: python -m src.contradiction.test_contradiction
"""
from .article_ids import top_level_article
from .divergent_precedent import detect_divergent_precedent
from .superseded_precedent import detect_superseded_precedent

# two Decisions, same Article, different Outcomes, no distinguishing facts -> flagged
decision_a = {
    "chunk_id": "dec:a",
    "cited_articles": ["33.3"],
    "outcome": "5 second time penalty.",
    "session": "Race",
    "fact": "Leaving the track without a justifiable reason.",
    "reason": "The Stewards reviewed video evidence.",
}
decision_b = {
    "chunk_id": "dec:b",
    "cited_articles": ["33.3"],
    "outcome": "10 second time penalty.",
    "session": "Race",
    "fact": "Leaving the track without a justifiable reason.",
    "reason": "The Stewards reviewed video evidence.",
}
flags = detect_divergent_precedent([decision_a, decision_b])
assert len(flags) == 1, flags
assert flags[0]["suppressed"] is False, flags[0]

# the same pair, but one Decision's Reason carries a repeat-offence
# Mitigating Factor -> the flag is suppressed, not dropped
decision_b_repeat = {
    **decision_b,
    "reason": "The car left the track after having received a 5 second time "
    "penalty on the fourth occasion.",
}
flags = detect_divergent_precedent([decision_a, decision_b_repeat])
assert len(flags) == 1, flags
assert flags[0]["suppressed"] is True, flags[0]
assert flags[0]["evidence"], "suppression must carry evidence, not just a bool"

# same Outcome -> not a divergence at all, no flag either way
decision_c = {**decision_b, "outcome": "5 second time penalty."}
assert detect_divergent_precedent([decision_a, decision_c]) == []

# a Decision predating a later Article amendment -> superseded
decision_old = {
    "chunk_id": "dec:old",
    "cited_articles": ["12"],
    "date": "2023-01-01",
}
article_changes = {
    "12": [
        {
            "changed_on": "2023-06-01",
            "from_issue": 3,
            "to_issue": 4,
            "change_summary": "text changed",
        }
    ]
}
flags = detect_superseded_precedent([decision_old], article_changes)
assert len(flags) == 1, flags
assert flags[0]["type"] == "superseded_precedent"
assert flags[0]["changed_on"] == "2023-06-01"

# a Decision *after* the amendment is not superseded by it
decision_new = {**decision_old, "chunk_id": "dec:new", "date": "2023-12-01"}
assert detect_superseded_precedent([decision_new], article_changes) == []

# top_level_article: sub-clause -> Article normalisation for change lookup
assert top_level_article("33.3") == "33"
assert top_level_article("12.2.1") == "12"
assert top_level_article("C3.14.4") == "C3"
assert top_level_article("44") == "44"
assert top_level_article("Appendix L Chapter IV Article 2(d)") is None

# a Decision citing a sub-clause, predating a change to the top-level
# Article, is flagged -- and the flag still reports the sub-clause, not
# the normalised Article
decision_subclause = {
    "chunk_id": "dec:sub",
    "cited_articles": ["12.2.1"],
    "date": "2023-01-01",
}
flags = detect_superseded_precedent([decision_subclause], article_changes)
assert len(flags) == 1, flags
assert flags[0]["article"] == "12.2.1", flags[0]
assert flags[0]["match_granularity"] == "article", flags[0]

# a bare Article citation that matches directly is "exact", not "article"
decision_bare = {"chunk_id": "dec:bare", "cited_articles": ["12"], "date": "2023-01-01"}
flags = detect_superseded_precedent([decision_bare], article_changes)
assert len(flags) == 1, flags
assert flags[0]["match_granularity"] == "exact", flags[0]

# an Appendix L (ISC) citation has no corpus counterpart -- not flagged,
# does not raise
decision_isc = {
    "chunk_id": "dec:isc",
    "cited_articles": ["Appendix L Chapter IV Article 2(d)"],
    "date": "2023-01-01",
}
assert detect_superseded_precedent([decision_isc], article_changes) == []

print(
    "OK — Divergent Precedent flags and suppresses correctly; "
    "Superseded Precedent fires only when the Decision predates the change."
)
