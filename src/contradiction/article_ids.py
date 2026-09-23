"""Normalise a Decision's cited Article ID to the top-level Article ID
article_changes.json is keyed by (CONTEXT.md: Phase 3 chunks Regulations at
top-level Article granularity, so change history is only tracked there).
"""
import re

_BARE_OR_PREFIXED = re.compile(r"^([A-Z]?\d+)(?:\.\d+)*$")


def top_level_article(cited_id: str) -> str | None:
    """"33.3" -> "33"; "12.2.1" -> "12"; "C3.14.4" -> "C3"; "44" -> "44".
    Appendix L / International Sporting Code citations have no corpus
    counterpart -- return None rather than guessing."""
    match = _BARE_OR_PREFIXED.match(cited_id.strip())
    return match.group(1) if match else None
