"""Best-effort metadata from a Regulation PDF's filename.

Filenames have no fixed schema across scrape eras (docs/RECON.md): plain
"2020_sporting_regulations_-_2019-04-30.pdf", issue-numbered
"fia_2023_formula_1_sporting_regulations_-_issue_1_-_2022-07-19.pdf", and the
2026+ lettered-section form
"fia_2026_f1_regulations_-_section_c_technical_-_iss_16_-_2026-02-27.pdf".
Every field is optional in the return value -- a filename that doesn't match
still gets processed, just with fewer metadata fields.
"""
import re

# Filenames separate words with underscores, which are \w characters, so \b
# does not fire at those boundaries -- match on the surrounding separator
# characters directly instead of relying on \b.
SEASON_RE = re.compile(r"(?<![\d])(19|20)\d{2}(?![\d])")
DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")
ISSUE_RE = re.compile(r"iss(?:ue)?[_\s]?0*(\d+)", re.I)
KIND_RE = re.compile(r"(sporting|technical|financial|operational)", re.I)
SECTION_RE = re.compile(r"section[_\s]([a-z])(?![a-z])", re.I)


def parse_filename(name: str) -> dict:
    season_m = SEASON_RE.search(name)
    date_m = DATE_RE.search(name)
    issue_m = ISSUE_RE.search(name)
    kind_m = KIND_RE.search(name)
    section_m = SECTION_RE.search(name)
    return {
        "season": int(season_m.group(0)) if season_m else None,
        "effective_date": date_m.group(1) if date_m else None,
        "issue": int(issue_m.group(1)) if issue_m else None,
        "kind": kind_m.group(1).lower() if kind_m else None,
        "section": section_m.group(1).upper() if section_m else None,
    }
