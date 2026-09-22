"""Phase 2 entry point: scrape 3 seasons of regulations (all issues) and
decisions for the controversy-targeted events, raw PDFs to data/raw/.

Usage: python -m src.scrape.run [--priority-only]
"""
import argparse
import sys

from . import fia
from .client import RateLimitedClient
from .storage import save

SEASONS = (2023, 2024, 2025)

# Events named in data/controversies.md (Phase 1) -- these get priority so a
# partial/interrupted run still covers the eval set's seeded contradictions.
PRIORITY_EVENTS = {
    2023: {
        "United States Grand Prix",
        "Austrian Grand Prix",
        "Singapore Grand Prix",
        "Qatar Grand Prix",
        "Australian Grand Prix",
        "Monaco Grand Prix",
    },
    2024: {
        "United States Grand Prix",
        "Mexico City Grand Prix",
        "Italian Grand Prix",
        "Saudi Arabian Grand Prix",
        "Austrian Grand Prix",
    },
}


def scrape_regulations(client: RateLimitedClient) -> int:
    urls = fia.list_regulation_pdfs(client)
    count = 0
    for url in urls:
        era = fia.era_for_url(url)
        save(client, url, "regulations", era=era, doc_type="regulation")
        count += 1
    return count


def scrape_event(client: RateLimitedClient, year: int, event_name: str, event_path: str) -> tuple[int, int]:
    pdfs = fia.list_event_pdfs(client, event_path)
    total = 0
    decisions = 0
    for href in pdfs:
        era = fia.era_for_url(href)
        is_decision = fia.is_decision_filename(href)
        save(
            client,
            href,
            f"decisions/{year}/{event_name}",
            era=era,
            doc_type="decision" if is_decision else "other",
            season=year,
            event=event_name,
        )
        total += 1
        decisions += int(is_decision)
    return total, decisions


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--priority-only",
        action="store_true",
        help="only scrape the controversy-targeted events (PLAN.md Phase 2 note: "
        "scrape all three seasons raw when doing a full run; this flag is for "
        "a faster first pass)",
    )
    args = parser.parse_args()

    client = RateLimitedClient()

    print("Regulations: fetching all issues, 2023-2025+...")
    reg_count = scrape_regulations(client)
    print(f"  {reg_count} regulation PDFs saved.")

    print("Discovering season slugs...")
    seasons = fia.list_season_slugs(client)
    for year in SEASONS:
        if year not in seasons:
            print(f"  WARNING: season {year} not found in dropdown, skipping.", file=sys.stderr)

    for year in SEASONS:
        slug = seasons.get(year)
        if not slug:
            continue
        print(f"Season {year} ({slug}): discovering events...")
        events = fia.list_event_urls(client, slug)
        target_events = (
            PRIORITY_EVENTS.get(year, set()) & set(events) if args.priority_only else set(events)
        )

        for name, path in events.items():
            if name not in target_events:
                continue
            total, decisions = scrape_event(client, year, name, path)
            print(f"  {name}: {total} PDFs ({decisions} decisions)")


if __name__ == "__main__":
    main()
