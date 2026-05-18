"""
crawler.py — Web crawler for COMP3011 Coursework 2.

This module is built incrementally across the development sessions. The
current scope is the foundation only: configuration, the page-result
container, the URL normaliser, and the in-scope check. BFS traversal,
HTTP fetching with retry, link extraction, and robots.txt handling are
added in later sessions.

Lecture references:
- Lecture 9 (Web Crawling): URL normalisation, single-domain restriction,
  politeness, and graceful failure.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable
from urllib.parse import urldefrag, urlparse

import requests


@dataclass
class CrawlResult:
    """A single fetched page. Returned by the fetch step in a later session."""

    url: str
    html: str
    status_code: int


@dataclass
class CrawlerConfig:
    """Configuration for the Crawler. Kept separate from the crawler itself so
    that tests can override individual fields without subclassing."""

    base_url: str = "https://quotes.toscrape.com/"
    delay_seconds: float = 6.0  # Brief mandates >= 6 seconds between requests.
    timeout_seconds: float = 10.0
    user_agent: str = "COMP3011-CW2-Crawler/1.0 (educational; respects robots.txt)"
    max_pages: int | None = None
    respect_robots: bool = True


class Crawler:
    """Web crawler with injectable HTTP session and sleeper.

    The session and sleeper are constructor parameters so the test suite can
    substitute mocks: no real network, no real 6-second waits. The class
    grows across sessions; the current implementation exposes only the
    constructor, the URL normaliser, and the scope check.
    """

    def __init__(
        self,
        config: CrawlerConfig | None = None,
        session: requests.Session | None = None,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        self.config = config or CrawlerConfig()
        self.session = session or requests.Session()
        self.sleeper = sleeper
        self.session.headers.update({"User-Agent": self.config.user_agent})
        self._domain: str = urlparse(self.config.base_url).netloc.lower()

    @staticmethod
    def normalise_url(url: str) -> str:
        """Return a canonical form of `url` so duplicates compare equal.

        Steps:
        1. Strip the `#fragment` — fragments never reach the server.
        2. Lowercase the scheme and host (per RFC 3986, both are
           case-insensitive).
        3. Leave the path as it was given (paths ARE case-sensitive on
           virtually all web servers).
        4. Add a root `/` when the path is empty so that `https://x.com`
           and `https://x.com/` do not produce two crawl entries.
        5. Preserve the query string when present.
        """
        defragged, _ = urldefrag(url)
        parsed = urlparse(defragged)
        scheme = parsed.scheme.lower()
        netloc = parsed.netloc.lower()
        path = parsed.path or "/"
        rebuilt = f"{scheme}://{netloc}{path}"
        if parsed.query:
            rebuilt += f"?{parsed.query}"
        return rebuilt

    def _is_in_scope(self, url: str) -> bool:
        """Return True if `url` is on the configured target domain.

        Host comparison is case-insensitive because the wire host might
        come in mixed case via redirects or anchor hrefs.
        """
        return urlparse(url).netloc.lower() == self._domain
