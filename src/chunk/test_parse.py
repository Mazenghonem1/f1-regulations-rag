"""Check: fuzzy label matching, both Article ID forms, dedupe.

Run: python -m src.chunk.test_parse
"""
from .decisions import cited_articles, parse_fields
from .dedupe import dedupe_decisions
from .regulations import split_articles

# fuzzy label matcher handles the "Infringment" misspelling
MISSPELLED_DECISION = """No / Driver    1 - Max Verstappen
Competitor Oracle Red Bull Racing
Session        Race
Fact           Left the track and gained an advantage.
Infringment    Alleged breach of Article 33.3 of the FIA Formula One Sporting Regulations.
Decision       Reprimand.
Reason         The Stewards reviewed video evidence.
"""
fields = parse_fields(MISSPELLED_DECISION)
assert fields["Infringement"] == (
    "Alleged breach of Article 33.3 of the FIA Formula One Sporting Regulations."
)
assert fields["Decision"] == "Reprimand."
assert cited_articles(fields["Infringement"]) == ["33.3"]

# boilerplate plural text must not be mistaken for a new field
BOILERPLATE_ONLY = """The Stewards have granted permission for car 24 to start.
Competitors are reminded that they have the right to appeal certain decisions of the Stewards.
Decisions of the Stewards are taken independently of the FIA.
"""
assert parse_fields(BOILERPLATE_ONLY) == {}

# both Article ID forms parse
assert cited_articles("Breach of Article 33.3 of the Sporting Regulations.") == ["33.3"]
assert cited_articles("Breach of Article C3.14.4 of the Technical Regulations.") == [
    "C3.14.4"
]
assert cited_articles("Breach of Appendix L, Chapter IV, Article 2 (d) of the Code.") == [
    "Appendix L Chapter IV Article 2(d)"
]

# regulation Article splitting: both notations, TOC dupes excluded
BARE_REG = """1)     REGULATIONS
1.1    The FIA will organise the Championship.

2)     GENERAL UNDERTAKING
2.1    All drivers undertake to observe the Code.
"""
articles = split_articles(BARE_REG)
assert [a["article_id"] for a in articles] == ["1", "2"]
assert "1.1" in articles[0]["sub_articles"]

SECTION_REG = """ARTICLE C4: MASS                                                                        60
ARTICLE C5: POWER UNIT                                                                  62

ARTICLE C4: MASS
C4.1      Minimum mass shall be 798kg.

ARTICLE C5: POWER UNIT
C5.1      Engine specification is fixed for the season.
"""
articles = split_articles(SECTION_REG)
ids = [a["article_id"] for a in articles]
assert ids == ["C4", "C5"], ids
c4 = articles[0]
assert "Minimum mass" in c4["body"]
assert "60" not in c4["title"]

# dedupe collapses a known duplicate pair, keyed on Document number not filename
records = [
    {"season": 2023, "event": "Austrian Grand Prix", "document_number": "27", "source_pdf": "a.pdf"},
    {"season": 2023, "event": "Austrian Grand Prix", "document_number": "27", "source_pdf": "a_0.pdf"},
    {"season": 2023, "event": "Austrian Grand Prix", "document_number": "50", "source_pdf": "b_0.pdf"},
]
kept, dropped = dedupe_decisions(records)
assert [r["source_pdf"] for r in kept] == ["a.pdf", "b_0.pdf"]
assert [r["source_pdf"] for r in dropped] == ["a_0.pdf"]

print("OK — fuzzy labels, both Article forms, and dedupe all behave as expected.")
