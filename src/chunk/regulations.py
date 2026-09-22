"""Split a Regulation PDF's extracted text into per-Article chunks.

Three Article header forms across doc kinds and eras (CONTEXT.md /
docs/RECON.md), all split at the same top-level granularity -- the chunk is
the whole Article, since that's the unit a citation points to. Sub-clause
text (3.6 a), C3.14.1) stays inline in the Article's body rather than
becoming its own chunk.

  Sporting, bare (2023-2025):         "33)  DRIVING"           -> Article "33"
  Technical, bare (2023-2025):        "ARTICLE 3: AERODYNAMIC.." -> Article "3"
  Section-prefixed (2026+):           "ARTICLE C4: MASS"        -> Article "C4"
"""
import re

# "33)  DRIVING" at column 0 -- a bare top-level Article header. Excludes
# indented sub-clause lines like "3.6    Each Competitor..." (those start
# with a dotted number, not "N)").
BARE_ARTICLE_RE = re.compile(r"^(\d{1,3})\)\s+([A-Z][A-Z0-9 ,'’\-/()]*)\s*$")

# "ARTICLE 3: AERODYNAMIC COMPONENTS" / "ARTICLE C4: MASS" -- Technical regs
# (bare number) and 2026+ section-prefixed regs (letter prefix) share this
# "ARTICLE <id>: <title>" header form. The table of contents repeats this
# exact line with a trailing page number ("ARTICLE C4: MASS    60"); a title
# ending in a bare number is what tells a TOC entry apart from the real
# section header, so it's rejected via a trailing optional group rather than
# folded into the charclass.
SECTION_ARTICLE_RE = re.compile(
    r"^ARTICLE\s+([A-Z]?\d{1,3}):\s*([A-Z][A-Z ,'’\-/()]*?)(?:\s+\d+)?\s*$"
)

# Repeating footer/header noise stamped on every page -- strip before
# chunking so it doesn't fragment or pollute Article bodies.
NOISE_RE = re.compile(
    r"^\s*(©\d{4}|20\d{2}.*(Regulations|Championship)\s+\d+/\d+|"
    r"SECTION [A-Z]:|Issue \d+\s*$)",
    re.I,
)

# "APPENDIX 1" etc. -- not an Article, but the last Article in a Regulation is
# followed only by Appendices with this header form (no "N)" or "ARTICLE N:"),
# so without an explicit stop here the last Article's body swallows every
# Appendix to end-of-document (verified: 2023 sporting Issues 1-2, Article 63
# body ballooning to >100k chars). Bounds the last Article the same way the
# next Article header bounds every other one.
APPENDIX_RE = re.compile(r"^\s*APPENDIX\s+\d+\b", re.I)


def _strip_noise(text: str) -> str:
    return "\n".join(line for line in text.splitlines() if not NOISE_RE.match(line))


# Sub-clause IDs within an Article's body, both notations: "33.3", "C3.14.4".
# Collected as metadata so a citation like "C3.14.4" can be matched to its
# containing Article chunk without splitting the chunk that finely.
SUB_ARTICLE_RE = re.compile(r"^([A-Z]?\d{1,3}(?:\.\d{1,3}){1,3})\s")


def _sub_articles(body: str) -> list[str]:
    found = []
    for line in body.splitlines():
        m = SUB_ARTICLE_RE.match(line)
        if m and m.group(1) not in found:
            found.append(m.group(1))
    return found


def split_articles(text: str) -> list[dict]:
    """Return [{article_id, title, body}], one per top-level Article, in
    document order. Text before the first Article header (title page,
    table of contents) is dropped."""
    text = _strip_noise(text)
    lines = text.splitlines()

    headers = []  # (line_index, article_id, title)
    appendix_lines = []
    for i, line in enumerate(lines):
        m = BARE_ARTICLE_RE.match(line)
        if m:
            headers.append((i, m.group(1), m.group(2).strip()))
            continue
        m = SECTION_ARTICLE_RE.match(line)
        if m:
            headers.append((i, m.group(1), m.group(2).strip()))
            continue
        if APPENDIX_RE.match(line):
            appendix_lines.append(i)

    # The table of contents lists "APPENDIX 1" too, long before the real
    # Appendix section -- only the first appendix marker *after* the last
    # Article header is the real section boundary.
    last_header = headers[-1][0] if headers else -1
    after_headers = [i for i in appendix_lines if i > last_header]
    appendix_start = min(after_headers, default=len(lines))

    candidates = []
    for idx, (start, article_id, title) in enumerate(headers):
        end = headers[idx + 1][0] if idx + 1 < len(headers) else appendix_start
        body = "\n".join(lines[start + 1 : end]).strip()
        candidates.append(
            {
                "article_id": article_id,
                "title": title,
                "body": body,
                "sub_articles": _sub_articles(body),
            }
        )

    # The table of contents produces one throwaway header per Article too
    # (immediately followed by the next TOC line, so its "body" is a thin
    # sliver); keep only the longest-bodied match per article_id, which is
    # always the real section, not the TOC listing.
    best: dict[str, dict] = {}
    order: list[str] = []
    for c in candidates:
        prev = best.get(c["article_id"])
        if prev is None:
            order.append(c["article_id"])
            best[c["article_id"]] = c
        elif len(c["body"]) > len(prev["body"]):
            best[c["article_id"]] = c
    return [best[aid] for aid in order]
