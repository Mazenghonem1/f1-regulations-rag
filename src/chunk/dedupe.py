"""Dedupe Decision records by extracted Document number, not filename.

Filenames with a "_0" suffix look like near-duplicates but are frequently
distinct documents (docs/RECON.md); the FIA's own Document number, printed
inside every Decision, is the only reliable dedupe key. Same
(season, event, document_number) keeps the first record seen.
"""


def dedupe_decisions(records: list[dict]) -> tuple[list[dict], list[dict]]:
    """Return (kept, dropped)."""
    seen = set()
    kept, dropped = [], []
    for r in records:
        if r.get("document_number") is None:
            kept.append(r)
            continue
        key = (r.get("season"), r.get("event"), r["document_number"])
        if key in seen:
            dropped.append(r)
        else:
            seen.add(key)
            kept.append(r)
    return kept, dropped
