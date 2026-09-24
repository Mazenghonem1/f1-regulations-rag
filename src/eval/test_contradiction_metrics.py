"""Check for _flagged_for_pair: the specific-pair scoring fix for the
per-Article metric-granularity gap found while widening contradiction-check
retrieval -- an unrelated same-Article flag must not count as a hit for a
question about a different, specific pair.

Run: python -m src.eval.test_contradiction_metrics
"""
from .contradiction_metrics import _flagged_for_article, _flagged_for_pair

divergent_a_vs_b = {
    "type": "divergent_precedent",
    "article": "33.3",
    "decisions": ["dec:a", "dec:b"],
    "suppressed": False,
}
divergent_c_vs_d_same_article = {
    "type": "divergent_precedent",
    "article": "33.3",
    "decisions": ["dec:c", "dec:d"],
    "suppressed": False,
}
divergent_a_vs_b_suppressed = {**divergent_a_vs_b, "suppressed": True}
superseded_x = {
    "type": "superseded_precedent",
    "article": "44",
    "decision": "dec:x",
    "suppressed": False,
}

# the exact pair is flagged -> hit
assert _flagged_for_pair([divergent_a_vs_b], ["dec:a", "dec:b"], "divergent_precedent") is True
# order doesn't matter
assert _flagged_for_pair([divergent_a_vs_b], ["dec:b", "dec:a"], "divergent_precedent") is True
# a different pair on the SAME Article must not count -- this is the bug
# _flagged_for_article has and _flagged_for_pair fixes
assert _flagged_for_pair([divergent_c_vs_d_same_article], ["dec:a", "dec:b"], "divergent_precedent") is False
# a suppressed flag for the exact pair is not a hit
assert _flagged_for_pair([divergent_a_vs_b_suppressed], ["dec:a", "dec:b"], "divergent_precedent") is False
# superseded_precedent: single decision id
assert _flagged_for_pair([superseded_x], ["dec:x"], "superseded_precedent") is True
assert _flagged_for_pair([superseded_x], ["dec:y"], "superseded_precedent") is False

# _flagged_for_article (the fallback for open-ended questions) still matches
# on Article alone, unchanged behaviour
assert _flagged_for_article([divergent_c_vs_d_same_article], "33.3", "divergent_precedent") is True
assert _flagged_for_article([divergent_a_vs_b_suppressed], "33.3", "divergent_precedent") is False

print("OK — _flagged_for_pair scores the specific gold pair, not just the shared Article.")
