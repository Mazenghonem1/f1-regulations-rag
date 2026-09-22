"""Rate-limited HTTP client for fia.com. Crawl-delay: 10 is non-negotiable."""
import time
import urllib.parse

import requests

CRAWL_DELAY_SECONDS = 10
BASE = "https://www.fia.com"


class RateLimitedClient:
    def __init__(self, delay=CRAWL_DELAY_SECONDS):
        self.delay = delay
        self._last_request = 0.0
        self.session = requests.Session()

    def get(self, url, **kwargs):
        if url.startswith("/"):
            url = BASE + urllib.parse.quote(url, safe="/:")
        elapsed = time.monotonic() - self._last_request
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)
        resp = self.session.get(url, timeout=30, **kwargs)
        self._last_request = time.monotonic()
        resp.raise_for_status()
        return resp
