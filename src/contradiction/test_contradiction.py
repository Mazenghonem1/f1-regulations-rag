"""Phase 6 check: two Decisions, same Article, different Outcomes -> flagged;
the same pair with a Mitigating Factor present -> not flagged; a Decision
predating an Article change -> superseded.

Run: python -m src.contradiction.test_contradiction
"""
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

print(
    "OK — Divergent Precedent flags and suppresses correctly; "
    "Superseded Precedent fires only when the Decision predates the change."
)
