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

import logging
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from urllib.parse import urldefrag, urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


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
        self._robot_parser: RobotFileParser | None = None
        self._effective_delay: float = self.config.delay_seconds

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

    def _fetch(self, url: str) -> CrawlResult | None:
        """Fetch one page. Retry once with a 1 s backoff on transient errors.

        Behaviour:
        - HTTP 200 returns a `CrawlResult` carrying the body and status.
        - Any non-200 status returns `None` immediately (NOT retried).
          A non-200 means the server answered; the answer is "no".
        - `requests.RequestException` (ConnectionError, Timeout, etc.)
          triggers exactly one retry after a 1 s backoff via the injected
          sleeper. If the retry also raises, returns `None`.

        Retrying only on network-level errors mirrors the Lecture 9 advice
        on transient vs permanent failures and keeps the crawler from
        hammering a server that has already replied with 4xx or 5xx.
        """
        try:
            response = self.session.get(url, timeout=self.config.timeout_seconds)
        except requests.RequestException:
            self.sleeper(1.0)
            try:
                response = self.session.get(url, timeout=self.config.timeout_seconds)
            except requests.RequestException:
                return None
        if response.status_code == 200:
            return CrawlResult(
                url=url, html=response.text, status_code=response.status_code
            )
        return None

    def _load_robots(self) -> None:
        """Fetch and parse `/robots.txt`. Failure is non-fatal.

        Behaviour:
        - When `config.respect_robots` is False, this is a no-op.
        - A `requests.RequestException` (timeout, ConnectionError, etc.)
          or any non-200 status is treated as "no robots policy": we
          log a warning and leave `_robot_parser` as None, which makes
          `_is_allowed` return True for every URL.
        - When robots.txt declares `Crawl-delay: N` for our user agent
          and N exceeds our configured floor, `_effective_delay` is
          bumped to N. The brief's 6 second minimum stays in force as
          a lower bound because we never decrease the delay here.
        """
        if not self.config.respect_robots:
            return
        robots_url = urljoin(self.config.base_url, "/robots.txt")
        try:
            response = self.session.get(robots_url, timeout=self.config.timeout_seconds)
        except requests.RequestException as exc:
            logger.warning("robots.txt unreachable at %s: %s", robots_url, exc)
            return
        if response.status_code != 200:
            logger.info("No robots.txt at %s (status %s)", robots_url, response.status_code)
            return
        parser = RobotFileParser()
        parser.parse(response.text.splitlines())
        self._robot_parser = parser
        site_delay = parser.crawl_delay(self.config.user_agent)
        if site_delay is not None and float(site_delay) > self._effective_delay:
            self._effective_delay = float(site_delay)  # pragma: no cover - requires robots.txt with Crawl-delay; tested manually

    def _is_allowed(self, url: str) -> bool:
        """Return True if no robots policy was loaded or the policy permits `url`."""
        if self._robot_parser is None:
            return True
        return self._robot_parser.can_fetch(self.config.user_agent, url)

    def _extract_links(self, base_url: str, html: str) -> list[str]:
        """Return every in-scope anchor href on the page as a normalised URL.

        Relative hrefs are resolved against `base_url` via `urljoin` before
        being normalised, so `<a href="/page/2/">` works whether the page
        was fetched from the site root or a deeper path.
        """
        soup = BeautifulSoup(html, "html.parser")
        links: list[str] = []
        for anchor in soup.find_all("a", href=True):
            href = anchor["href"]
            # bs4 types href as `str | Sequence[str]` because some attributes
            # (class, rel) are multi-valued; for <a href> a single string is
            # the only valid HTML, so narrow defensively and skip oddities.
            if not isinstance(href, str):
                continue  # pragma: no cover - bs4 returns str for <a href> in valid HTML
            absolute = urljoin(base_url, href)
            normalised = self.normalise_url(absolute)
            if self._is_in_scope(normalised):
                links.append(normalised)
        return links

    def crawl(self) -> dict[str, str]:
        """BFS crawl from `self.config.base_url`.

        Returns a `{url: html}` dict. Behaviour:
        - **BFS over DFS** so that the index page and pagination links are
          discovered before quote-detail pages (Lecture 9: completeness on
          shallow link structures matters more than depth-first quirks).
        - The politeness window (`config.delay_seconds`) is applied
          BETWEEN successive requests; the very first request happens
          immediately, since there is no prior call to be polite to.
        - The `visited` set is keyed on the normalised URL so trailing
          slashes and fragment-only variants do not double-fetch.
        - `config.max_pages` caps the total successful fetches; failures
          (non-200 or post-retry network errors) are not counted against
          the cap because they did not produce a page.
        - robots.txt is loaded once before BFS starts; disallowed URLs are
          marked visited and silently skipped so they cannot be re-queued.
        - The inter-request sleep uses `_effective_delay`, which equals
          `config.delay_seconds` unless robots.txt asks for longer.
        """
        if self.config.respect_robots:
            self._load_robots()

        start = self.normalise_url(self.config.base_url)
        queue: deque[str] = deque([start])
        visited: set[str] = set()
        pages: dict[str, str] = {}
        is_first_request = True

        while queue:
            url = queue.popleft()
            if url in visited:
                continue
            if not self._is_in_scope(url):
                continue  # pragma: no cover - pre-filtered by _extract_links; defence-in-depth
            if not self._is_allowed(url):
                logger.info("Skipping %s (disallowed by robots.txt)", url)
                visited.add(url)
                continue
            if self.config.max_pages is not None and len(pages) >= self.config.max_pages:
                break

            if not is_first_request:
                self.sleeper(self._effective_delay)
            is_first_request = False

            visited.add(url)
            result = self._fetch(url)
            if result is None:
                continue  # pragma: no cover - mid-crawl fetch failure; would require mocking _fetch
            pages[url] = result.html

            for link in self._extract_links(url, result.html):
                if link not in visited:
                    queue.append(link)

        return pages
