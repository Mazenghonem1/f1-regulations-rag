"""Parse one Stewards' Decision PDF's extracted text into structured fields.

Label vocabulary per CONTEXT.md / docs/RECON.md: No / Driver, Competitor,
Session, Fact, Infringement, Decision, Reason. Matched fuzzily -- at least
one 2023 document misspells "Infringement" as "Infringment".
"""
import difflib
import re

LABELS = [
    "No / Driver",
    "Competitor",
    "Time",
    "Session",
    "Fact",
    "Infringement",
    "Decision",
    "Reason",
]

# Labels sit flush against the left margin with no fixed column gap
# ("Competitor Williams Racing" vs "No / Driver    23 - ..."), so match by
# trying each label as a fuzzy prefix rather than splitting on whitespace.
_LEADING_WORDS_RE = re.compile(r"^\s*([A-Za-z/ ]{2,20}?)\s(.*)$")

DOCUMENT_NUMBER_RE = re.compile(r"Document\s+(\d+)")
# "Date       02 April 2023" sits on the same physical line as the "To" field
# (a two-column header layout), not as its own flush-left label -- doesn't
# fit the LABELS scheme above, needs its own line-anywhere search.
DATE_RE = re.compile(r"Date\s+(\d{1,2}\s+\w+\s+\d{4})")
_MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11,
    "december": 12,
}
# Bare/section-prefixed regulation articles: 33.3, C3.14.4. Also matches a
# whole-Article citation with no sub-clause ("Article 44") when it directly
# follows the word "Article", without matching every bare number in the text.
ARTICLE_RE = re.compile(r"\b([A-Z]?\d+(?:\.\d+)+)\b")
WHOLE_ARTICLE_RE = re.compile(r"\bArticle\s+(\d+)\b(?!\.\d)")
# Appendix L (International Sporting Code driving standards) citations look
# like "Appendix L, Chapter IV, Article 2 (d)" -- no dotted number, so they
# need their own pattern rather than widening ARTICLE_RE into false positives.
APPENDIX_ARTICLE_RE = re.compile(
    r"Appendix\s+([A-Z]),?\s+Chapter\s+([IVXLC]+),?\s+Article\s+(\d+)\s*\(?([a-z])?\)?",
    re.I,
)

# Longest labels first so "No / Driver" isn't shadowed by a shorter partial.
_LABELS_BY_LENGTH = sorted(LABELS, key=len, reverse=True)


def _match_label(line: str) -> tuple[str, str] | None:
    """Return (label, rest_of_line) if `line` starts with a label at column
    0, fuzzily (handles the "Infringment" misspelling), else None.

    Labels are flush left; continuation text (e.g. Reason's indented
    paragraphs, which include boilerplate sentences like "Competitors are
    reminded...") is indented, so requiring no leading whitespace stops
    those from being mistaken for a new field.
    """
    if line[:1].isspace():
        return None
    stripped = line.strip()
    for label in _LABELS_BY_LENGTH:
        if stripped.startswith(label):
            rest = stripped[len(label):]
            # Reject a bare-prefix false match ("Competitor" prefixing the
            # boilerplate sentence "Competitors are reminded...") -- a real
            # label is followed by whitespace or end of line, not a letter.
            if rest and not rest[0].isspace():
                continue
            return label, rest.strip()
    m = _LEADING_WORDS_RE.match(line)
    if not m:
        return None
    lead, rest = m.group(1).strip(), m.group(2)
    if lead in {label + "s" for label in LABELS}:
        # Plural boilerplate ("Competitors are reminded...", "Decisions of
        # the Stewards are taken...") reads as a near-match to the singular
        # label but is prose, not a new field.
        return None
    match = difflib.get_close_matches(lead, LABELS, n=1, cutoff=0.82)
    if match:
        return match[0], rest.strip()
    return None


def parse_fields(text: str) -> dict:
    """Split extracted text into the fixed label vocabulary. Multi-line
    values (e.g. Reason) are joined until the next recognised label starts."""
    fields: dict[str, list[str]] = {}
    current = None
    for line in text.splitlines():
        matched = _match_label(line)
        if matched:
            current, rest = matched
            fields.setdefault(current, [])
            if rest:
                fields[current].append(rest)
        elif current and line.strip():
            fields[current].append(line.strip())
    return {k: " ".join(v).strip() for k, v in fields.items()}


def document_number(text: str) -> str | None:
    m = DOCUMENT_NUMBER_RE.search(text)
    return m.group(1) if m else None


def decision_date(text: str) -> str | None:
    """Return the Decision's issue date as ISO "YYYY-MM-DD", parsed from the
    "Date DD Month YYYY" header field, or None if absent/unparseable."""
    m = DATE_RE.search(text)
    if not m:
        return None
    day_s, month_s, year_s = m.group(1).split()
    month = _MONTHS.get(month_s.lower())
    if month is None:
        return None
    return f"{year_s}-{month:02d}-{int(day_s):02d}"


def cited_articles(infringement_text: str) -> list[str]:
    appendix_matches = APPENDIX_ARTICLE_RE.findall(infringement_text)
    # Appendix citations don't use a dotted number ("Article 2 (d)"), so
    # strip them before the whole-Article fallback runs -- otherwise "2"
    # gets counted twice, once bare and once as part of the Appendix label.
    remainder = APPENDIX_ARTICLE_RE.sub("", infringement_text)

    articles = list(ARTICLE_RE.findall(remainder))
    if not articles:
        articles = WHOLE_ARTICLE_RE.findall(remainder)
    for appendix, chapter, article, sub in appendix_matches:
        label = f"Appendix {appendix} Chapter {chapter} Article {article}"
        if sub:
            label += f"({sub})"
        articles.append(label)
    return articles


def parse_decision(text: str, source_meta: dict) -> dict:
    """Full structured record for one Decision document."""
    fields = parse_fields(text)
    infringement = fields.get("Infringement", "")
    fact = fields.get("Fact", "")
    # A handful of documents swap Fact/Infringement content (the Article
    # citation lands in Fact instead) -- fall back rather than lose the
    # citation to a source-side labelling inconsistency.
    articles = cited_articles(infringement) or cited_articles(fact)
    # Right of Review / Protest / Summons / administrative documents share
    # the "decision|infringement|offence|protest" filename filter but are
    # free-text legal rulings, not the fixed-label per-incident template --
    # they carry none of Fact/Infringement/Decision. Flagged rather than
    # dropped, and excluded from the field-coverage bar in run.py, since the
    # template those fields belong to doesn't apply to them.
    is_incident_template = bool(fields.get("Fact") or fields.get("Infringement") or fields.get("Decision"))
    return {
        **source_meta,
        "document_number": document_number(text),
        "date": decision_date(text),
        "is_incident_template": is_incident_template,
        "driver_no": fields.get("No / Driver"),
        "competitor": fields.get("Competitor"),
        "session": fields.get("Session"),
        "fact": fact or None,
        "infringement": infringement or None,
        "cited_articles": articles,
        "outcome": fields.get("Decision"),
        "reason": fields.get("Reason"),
    }
