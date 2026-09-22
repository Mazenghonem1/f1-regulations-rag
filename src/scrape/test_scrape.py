"""Phase 2 check: era-routing and the Decision filename filter.

Run: python -m src.scrape.test_scrape
"""
from .fia import era_for_url, is_decision_filename

# era routing
assert (
    era_for_url(
        "https://www.fia.com/system/files/decision-document/"
        "2025_abu_dhabi_grand_prix_-_decision_-_car_4_-_alleged_leaving_the_track.pdf"
    )
    == "2025+"
)
assert (
    era_for_url(
        "/sites/default/files/decision-document/"
        "2023 Monaco Grand Prix - Infringement - Car 63 - Unsafe Rejoin.pdf"
    )
    == "<=2024"
)
try:
    era_for_url("https://www.fia.com/nowhere/file.pdf")
    assert False, "expected ValueError for unrecognised era"
except ValueError:
    pass

# Decision filter: accepts known Decisions
assert is_decision_filename(
    "/system/files/decision-document/2025_abu_dhabi_grand_prix_-_infringement_-_car_18_-_more_than_one_change_of_direction.pdf"
)
assert is_decision_filename(
    "/sites/default/files/decision-document/2023 Monaco Grand Prix - Infringement - Car 63 - Unsafe Rejoin.pdf"
)
assert is_decision_filename("2024 Some Grand Prix - Protest - Car 1.pdf")
assert is_decision_filename("2024 Some Grand Prix - Offence - Car 1.pdf")

# ...and rejects a classification/non-decision document, even though the
# full URL contains "decision-document" in its fixed path segment.
assert not is_decision_filename(
    "/system/files/decision-document/2025_abu_dhabi_grand_prix_-_final_race_classification.pdf"
)
assert not is_decision_filename(
    "/system/files/decision-document/2025_abu_dhabi_grand_prix_-_race_scrutineering.pdf"
)
assert not is_decision_filename(
    "/system/files/decision-document/2025_abu_dhabi_grand_prix_-_championship_points.pdf"
)

print("OK — era routing and Decision filter both behave as expected.")
