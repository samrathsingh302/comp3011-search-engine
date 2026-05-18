"""Tests for src.crawler. No real network, no real sleep — every dependency is mocked."""

from __future__ import annotations

from unittest.mock import MagicMock

from src.crawler import Crawler, CrawlerConfig, CrawlResult


def _make_session() -> MagicMock:
    """Build a stand-in for requests.Session with a real-dict headers field."""
    session = MagicMock()
    session.headers = {}
    return session


class TestNormaliseUrl:
    def test_strips_fragment(self) -> None:
        assert (
            Crawler.normalise_url("https://EXAMPLE.com/page#section")
            == "https://example.com/page"
        )

    def test_lowercases_host_not_path(self) -> None:
        assert (
            Crawler.normalise_url("https://EXAMPLE.com/PaTh")
            == "https://example.com/PaTh"
        )

    def test_adds_root_slash_when_path_missing(self) -> None:
        assert Crawler.normalise_url("https://example.com") == "https://example.com/"

    def test_preserves_query_string_and_strips_only_fragment(self) -> None:
        assert (
            Crawler.normalise_url("https://example.com/p?q=1&r=2#frag")
            == "https://example.com/p?q=1&r=2"
        )


class TestIsInScope:
    def test_same_domain_is_in_scope(self) -> None:
        crawler = Crawler(
            config=CrawlerConfig(base_url="https://quotes.toscrape.com/"),
            session=_make_session(),
        )
        assert crawler._is_in_scope("https://quotes.toscrape.com/page/2/") is True

    def test_external_domain_is_out_of_scope(self) -> None:
        crawler = Crawler(
            config=CrawlerConfig(base_url="https://quotes.toscrape.com/"),
            session=_make_session(),
        )
        assert crawler._is_in_scope("https://external.example.com/") is False

    def test_host_casing_does_not_matter(self) -> None:
        """Case-insensitive host comparison guards against mixed-case anchor hrefs."""
        crawler = Crawler(
            config=CrawlerConfig(base_url="https://Quotes.ToScrape.Com/"),
            session=_make_session(),
        )
        assert crawler._is_in_scope("https://quotes.toscrape.com/page/3/") is True


class TestInit:
    def test_user_agent_set_on_session(self) -> None:
        session = _make_session()
        Crawler(session=session)
        assert "User-Agent" in session.headers
        assert "COMP3011" in session.headers["User-Agent"]

    def test_default_config_used_when_none_given(self) -> None:
        crawler = Crawler(session=_make_session())
        assert isinstance(crawler.config, CrawlerConfig)
        assert crawler.config.delay_seconds == 6.0
        assert crawler.config.max_pages is None
        assert crawler.config.respect_robots is True


class TestDataclasses:
    def test_crawl_result_holds_url_html_and_status(self) -> None:
        result = CrawlResult(url="https://example.com/", html="<html></html>", status_code=200)
        assert result.url == "https://example.com/"
        assert result.html == "<html></html>"
        assert result.status_code == 200

    def test_brief_compliance_default_delay_meets_six_seconds(self) -> None:
        """The coursework brief mandates at least 6 seconds between requests."""
        assert CrawlerConfig().delay_seconds >= 6.0
