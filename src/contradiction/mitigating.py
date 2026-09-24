"""Justified Distinction suppression (ADR 0002) -- the precision half of
Divergent Precedent detection. Different Outcomes on the same Article are
often *correct* because the facts differ (CONTEXT.md): wet vs dry, first vs
repeat offence, racing incident vs deliberate act, different session.

Verified against real data: 2023 Austrian GP Article 33.3 decisions --
a 10s penalty explicitly cites "after having received a 5 second time
penalty on the fourth occasion" (repeat offence) against otherwise-identical
5s decisions citing only "on the third occasion". That escalation language
is the signal this module looks for.
"""
import re

_ORDINAL_WORDS = {
    "first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5,
    "sixth": 6, "seventh": 7, "eighth": 8, "ninth": 9, "tenth": 10,
}
# "on the fourth (4th) occasion" -- the escalation point ("this is the Nth
# time"), not the running total ("seven occasions" so far). Deliberately
# matches only the ordinal ("the Nth occasion") form, not the cardinal
# ("N occasions") form, since it's the specific occasion a prior sanction
# was escalated from that's comparable across Decisions -- the running
# total alone doesn't say when the penalty stepped up. Two Decisions both
# citing a repeat offence are NOT the same Justified Distinction if this
# differs (verified: 2023 Austrian GP Article 33.3 -- a decision noting a
# prior 5s *penalty* on the 4th occasion got 10s, one noting only a prior
# black-and-white *flag* on the 3rd occasion got 5s; treating both as
# merely "repeat_offence" without the occasion/prior-sanction-kind would
# wrongly suppress that pair).
#
# A compound form also occurs ("on the fourth (4th) and fifth (5th)
# occasions" -- 2023 Qatar GP Document 81, verified false-negative on
# is_justified_distinction: the original singular-only "occasion" pattern
# didn't match "occasions" at all, so this real Decision's occasion_count
# read as None, wrongly suppressing a genuine divergence against Document
# 66). The first ordinal is the one that matters -- it's the occasion the
# prior sanction was escalated from, same as the single-ordinal form.
OCCASION_COUNT_RE = re.compile(
    r"on the (\w+)(?:\s*\(\d+\w{0,2}\))?(?:\s+and\s+\w+\s*\(\d+\w{0,2}\))?\s+occasions?", re.I
)
# The article ("a"/"the") is optional -- the plural compound form ("received
# 5 second time penalties on the fourth and fifth occasions", Document 81)
# drops it entirely, unlike the singular form ("received a ... penalty").
PRIOR_PENALTY_RE = re.compile(r"after having received (?:(?:a|the)\s+)?[\w .-]*?penalt(?:y|ies)", re.I)
PRIOR_FLAG_RE = re.compile(r"after having received (?:(?:a|the)\s+)?[\w .-]*?(flag|warning)", re.I)
WET_DRY_RE = re.compile(r"\b(wet|dry|intermediate|rain)\b", re.I)
INTENT_RE = re.compile(r"\b(deliberate|intentional|racing incident|no intent)\b", re.I)


def _occasion_count(text: str) -> int | None:
    m = OCCASION_COUNT_RE.search(text)
    if not m:
        return None
    word = m.group(1).lower()
    if word.isdigit():
        return int(word)
    return _ORDINAL_WORDS.get(word)


def mitigating_factors(decision: dict) -> dict:
    """Return the Mitigating Factor evidence found in a Decision's Fact +
    Reason text: occasion_count (int or None), prior_sanction ("penalty",
    "flag", or None), wet_dry (bool), intent (bool). An empty-valued dict
    means no distinguishing evidence was found in the text."""
    text = f"{decision.get('fact') or ''} {decision.get('reason') or ''}"
    prior_sanction = None
    if PRIOR_PENALTY_RE.search(text):
        prior_sanction = "penalty"
    elif PRIOR_FLAG_RE.search(text):
        prior_sanction = "flag"
    return {
        "occasion_count": _occasion_count(text),
        "prior_sanction": prior_sanction,
        "wet_dry": bool(WET_DRY_RE.search(text)),
        "intent": bool(INTENT_RE.search(text)),
    }


def is_justified_distinction(decision_a: dict, decision_b: dict) -> tuple[bool, list[str]]:
    """Two Decisions differ if their Mitigating Factor evidence disagrees --
    a different occasion count, a different prior-sanction kind (a Decision
    escalating from an actual penalty is not the same fact pattern as one
    escalating from a flag/warning), wet vs dry, intent language, or a
    different Session. A Divergent Precedent flag between them should be
    suppressed. Returns (suppressed, evidence)."""
    evidence = []
    factors_a, factors_b = mitigating_factors(decision_a), mitigating_factors(decision_b)
    for key in ("occasion_count", "prior_sanction", "wet_dry", "intent"):
        va, vb = factors_a[key], factors_b[key]
        if va != vb and (va or vb):
            evidence.append(f"{key} differs: {va!r} vs {vb!r}")
    session_a, session_b = decision_a.get("session"), decision_b.get("session")
    if session_a and session_b and session_a != session_b:
        evidence.append(f"different session: {session_a} vs {session_b}")
    return bool(evidence), evidence
