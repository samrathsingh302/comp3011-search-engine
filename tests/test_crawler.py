"""Tests for src.crawler. No real network, no real sleep — every dependency is mocked."""

from __future__ import annotations

from unittest.mock import MagicMock

import requests

from src.crawler import Crawler, CrawlerConfig, CrawlResult


def _make_session() -> MagicMock:
    """Build a stand-in for requests.Session with a real-dict headers field."""
    session = MagicMock()
    session.headers = {}
    return session


def _make_response(text: str = "", status: int = 200) -> MagicMock:
    """Build a stand-in for requests.Response."""
    response = MagicMock()
    response.text = text
    response.status_code = status
    return response


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


class TestFetch:
    def test_returns_crawl_result_on_200(self) -> None:
        session = _make_session()
        session.get.return_value = _make_response(text="<html>hi</html>", status=200)
        crawler = Crawler(session=session, sleeper=MagicMock())
        result = crawler._fetch("https://quotes.toscrape.com/")
        assert isinstance(result, CrawlResult)
        assert result.url == "https://quotes.toscrape.com/"
        assert result.html == "<html>hi</html>"
        assert result.status_code == 200

    def test_returns_none_on_503_without_retry(self) -> None:
        """Non-200 means the server answered; we do NOT retry on those."""
        session = _make_session()
        session.get.return_value = _make_response(status=503)
        sleeper = MagicMock()
        crawler = Crawler(session=session, sleeper=sleeper)
        assert crawler._fetch("https://quotes.toscrape.com/") is None
        assert session.get.call_count == 1
        sleeper.assert_not_called()

    def test_retries_once_on_connection_error_then_succeeds(self) -> None:
        session = _make_session()
        ok = _make_response(text="<html>ok</html>", status=200)
        session.get.side_effect = [requests.ConnectionError("transient"), ok]
        sleeper = MagicMock()
        crawler = Crawler(session=session, sleeper=sleeper)
        result = crawler._fetch("https://quotes.toscrape.com/")
        assert isinstance(result, CrawlResult)
        assert result.html == "<html>ok</html>"
        assert session.get.call_count == 2
        sleeper.assert_called_once_with(1.0)

    def test_gives_up_after_second_connection_error(self) -> None:
        session = _make_session()
        session.get.side_effect = requests.ConnectionError("persistent")
        sleeper = MagicMock()
        crawler = Crawler(session=session, sleeper=sleeper)
        assert crawler._fetch("https://quotes.toscrape.com/") is None
        assert session.get.call_count == 2
        sleeper.assert_called_once_with(1.0)

    def test_request_uses_configured_timeout(self) -> None:
        """The injected timeout should reach the underlying session call."""
        session = _make_session()
        session.get.return_value = _make_response(status=200)
        config = CrawlerConfig(timeout_seconds=2.5)
        crawler = Crawler(config=config, session=session, sleeper=MagicMock())
        crawler._fetch("https://quotes.toscrape.com/")
        _, kwargs = session.get.call_args
        assert kwargs.get("timeout") == 2.5
