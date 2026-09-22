"""fia.com source: season/event discovery, regulation listing, decision filtering.

Two URL eras (docs/RECON.md):
  2025+   /system/files/...            underscores, lowercase
  <=2024  /sites/default/files/...     spaces, title case (URL-encoded on fetch)

Never construct season slugs or node URLs -- scrape from dropdowns, and only
use /documents/... aliases (canonical /node/<id> is robots.txt-disallowed).
"""
import re

from .client import RateLimitedClient

CHAMPIONSHIP_PATH = "/documents/championships/fia-formula-one-world-championship-14"
REGULATIONS_URL = "https://www.fia.com/regulation/category/110"

DECISION_FILENAME_RE = re.compile(r"decision|infringement|offence|protest", re.I)
PDF_HREF_RE = re.compile(r'href="([^"]+\.pdf)"')
SEASON_OPTION_RE = re.compile(
    r'<option[^>]*value="(/documents/championships/fia-formula-one-world-championship-14/season/(season-[\w-]+))"[^>]*>\s*SEASON\s+(\d{4})',
    re.I,
)
EVENT_OPTION_RE = re.compile(
    r'<option[^>]*value="(/documents/championships/fia-formula-one-world-championship-14/season/season-[\w-]+/event/[^"]+)"[^>]*>([^<]+)</option>'
)


def era_for_url(url: str) -> str:
    """Classify a PDF URL by the two known path eras."""
    if "/system/files/" in url:
        return "2025+"
    if "/sites/default/files/" in url:
        return "<=2024"
    raise ValueError(f"unrecognised URL era: {url}")


def is_decision_filename(url_or_name: str) -> bool:
    """Only the filename, not the fixed /decision-document/ path segment, is matched."""
    name = url_or_name.rsplit("/", 1)[-1]
    return bool(DECISION_FILENAME_RE.search(name))


def list_season_slugs(client: RateLimitedClient) -> dict[int, str]:
    """year -> season slug, scraped from the dropdown on the championship page."""
    resp = client.get(CHAMPIONSHIP_PATH)
    seasons = {}
    for _, slug, year in SEASON_OPTION_RE.findall(resp.text):
        seasons[int(year)] = slug
    return seasons


def list_event_urls(client: RateLimitedClient, season_slug: str) -> dict[str, str]:
    """event name -> event page path, scraped from the dropdown on a season page."""
    url = f"{CHAMPIONSHIP_PATH}/season/{season_slug}"
    resp = client.get(url)
    events = {}
    for path, name in EVENT_OPTION_RE.findall(resp.text):
        events[name.strip()] = path
    return events


def list_event_pdfs(client: RateLimitedClient, event_path: str) -> list[str]:
    resp = client.get(event_path)
    return PDF_HREF_RE.findall(resp.text)


def list_regulation_pdfs(client: RateLimitedClient) -> list[str]:
    resp = client.get(REGULATIONS_URL)
    return PDF_HREF_RE.findall(resp.text)
