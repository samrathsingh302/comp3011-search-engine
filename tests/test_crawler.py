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


def _session_serving(pages: dict[str, str]) -> MagicMock:
    """Build a fake `requests.Session` whose `.get()` returns canned HTML by URL.

    Unknown URLs respond with a 404 so that out-of-fixture requests are
    visible in test failures rather than silently returning empty 200s.
    """
    session = _make_session()

    def fake_get(url: str, *args: object, **kwargs: object) -> MagicMock:
        if url in pages:
            return _make_response(text=pages[url], status=200)
        return _make_response(status=404)

    session.get.side_effect = fake_get
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


class TestBfsCrawl:
    def test_crawler_does_not_sleep_before_first_request(self) -> None:
        """No prior request exists; the politeness window cannot apply."""
        session = _session_serving({"https://quotes.toscrape.com/": ""})
        sleeper = MagicMock()
        crawler = Crawler(session=session, sleeper=sleeper)
        crawler.crawl()
        sleeper.assert_not_called()

    def test_crawler_sleeps_between_requests(self) -> None:
        session = _session_serving({
            "https://quotes.toscrape.com/": '<a href="/page/2/">2</a>',
            "https://quotes.toscrape.com/page/2/": "",
        })
        sleeper = MagicMock()
        crawler = Crawler(
            config=CrawlerConfig(delay_seconds=6.0),
            session=session,
            sleeper=sleeper,
        )
        crawler.crawl()
        delays = [call.args[0] for call in sleeper.call_args_list]
        assert 6.0 in delays

    def test_crawler_stays_in_domain(self) -> None:
        """An anchor pointing at a different netloc must be ignored."""
        session = _session_serving({
            "https://quotes.toscrape.com/": '<a href="https://external.example.com/">x</a>',
        })
        crawler = Crawler(session=session, sleeper=MagicMock())
        result = crawler.crawl()
        assert list(result.keys()) == ["https://quotes.toscrape.com/"]

    def test_crawler_avoids_duplicate_urls(self) -> None:
        """Three anchors to the same href should produce exactly one fetch."""
        session = _session_serving({
            "https://quotes.toscrape.com/": (
                '<a href="/page/2/">a</a> '
                '<a href="/page/2/">b</a> '
                '<a href="/page/2/">c</a>'
            ),
            "https://quotes.toscrape.com/page/2/": "",
        })
        crawler = Crawler(session=session, sleeper=MagicMock())
        result = crawler.crawl()
        assert len(result) == 2
        get_urls = [call.args[0] for call in session.get.call_args_list]
        assert get_urls.count("https://quotes.toscrape.com/page/2/") == 1

    def test_crawler_respects_max_pages(self) -> None:
        """With a cap of 2, only 2 pages are returned even when 3 are reachable."""
        session = _session_serving({
            "https://quotes.toscrape.com/": '<a href="/page/2/">2</a>',
            "https://quotes.toscrape.com/page/2/": '<a href="/page/3/">3</a>',
            "https://quotes.toscrape.com/page/3/": "",
        })
        crawler = Crawler(
            config=CrawlerConfig(max_pages=2),
            session=session,
            sleeper=MagicMock(),
        )
        result = crawler.crawl()
        assert len(result) == 2


class TestRobots:
    def test_crawler_robots_txt_blocks_path(self) -> None:
        """A path disallowed by robots.txt is skipped, siblings are still crawled."""
        session = _session_serving({
            "https://quotes.toscrape.com/robots.txt": "User-agent: *\nDisallow: /blocked\n",
            "https://quotes.toscrape.com/": (
                '<a href="/blocked">x</a> <a href="/ok">y</a>'
            ),
            "https://quotes.toscrape.com/blocked": "should not appear",
            "https://quotes.toscrape.com/ok": "fine",
        })
        crawler = Crawler(session=session, sleeper=MagicMock())
        result = crawler.crawl()
        assert "https://quotes.toscrape.com/blocked" not in result
        assert "https://quotes.toscrape.com/ok" in result

    def test_crawler_handles_missing_robots_txt(self) -> None:
        """A network failure on /robots.txt must not abort the crawl."""
        session = _make_session()

        def fake_get(url: str, *args: object, **kwargs: object) -> MagicMock:
            if url.endswith("/robots.txt"):
                raise requests.ConnectionError("no robots")
            return _make_response(text="<html><body>ok</body></html>", status=200)

        session.get.side_effect = fake_get
        crawler = Crawler(session=session, sleeper=MagicMock())
        result = crawler.crawl()
        assert "https://quotes.toscrape.com/" in result

    def test_crawler_default_delay_is_six_seconds(self) -> None:
        """Synonym for the brief-compliance test; ensures the prompt's name exists."""
        assert CrawlerConfig().delay_seconds >= 6.0
