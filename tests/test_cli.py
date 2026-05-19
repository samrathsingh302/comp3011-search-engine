"""CLI tests with mocked Crawler and a real in-memory inverted index.

Captures stdout via `io.StringIO` and `contextlib.redirect_stdout` so the
tests can assert on what the shell actually prints. The `src.cli.Crawler`
symbol is monkeypatched at module level so `do_build` never hits the
network.
"""

from __future__ import annotations

import contextlib
import io
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from src.cli import Shell
from src.indexer import InvertedIndex
from src.search import SearchEngine
from src.storage import save_index


class FakeCrawler:
    """Stand-in for src.crawler.Crawler that returns canned pages without network."""

    def __init__(
        self,
        config: Any = None,
        session: Any = None,
        sleeper: Any = None,
    ) -> None:
        self.config = config
        self._pages = {
            "http://fake.example.com/": (
                "<html><head><title>Fake Title</title></head>"
                "<body>cat dog cat fish bird</body></html>"
            ),
        }

    def crawl(self) -> dict[str, str]:
        return dict(self._pages)


def _capture(callable_: Callable[[], Any]) -> str:
    """Run `callable_` and return whatever it wrote to stdout."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        callable_()
    return buf.getvalue()


def _build_small_index() -> InvertedIndex:
    idx = InvertedIndex()
    idx.add_document(
        "http://a.example.com/",
        "<html><head><title>Cats</title></head>"
        "<body>cat dog cat fish</body></html>",
    )
    idx.add_document(
        "http://b.example.com/",
        "<html><head><title>Animals</title></head>"
        "<body>cat bird</body></html>",
    )
    return idx


@pytest.fixture
def shell_without_engine(tmp_path: Path) -> Shell:
    return Shell(index_path=tmp_path / "test_index.json")


@pytest.fixture
def shell_with_engine(tmp_path: Path) -> Shell:
    shell = Shell(index_path=tmp_path / "test_index.json")
    shell.index = _build_small_index()
    shell.engine = SearchEngine(shell.index)
    return shell


class TestHelp:
    def test_help_lists_commands(self, shell_without_engine: Shell) -> None:
        """`cmd.Cmd.do_help` writes to `self.stdout` (captured at __init__), not to
        `sys.stdout`, so we override `shell.stdout` directly here. `redirect_stdout`
        alone misses it because the bound reference was taken before the patch."""
        buf = io.StringIO()
        shell_without_engine.stdout = buf
        shell_without_engine.onecmd("help")
        out = buf.getvalue()
        for command in ("build", "find", "exit", "load", "print", "stats"):
            assert command in out


class TestBuild:
    def test_build_runs_crawler_and_saves(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """do_build constructs the mocked Crawler, persists the index, and sets the engine."""
        target = tmp_path / "out.json"
        monkeypatch.setattr("src.cli.Crawler", FakeCrawler)
        shell = Shell(index_path=target)
        out = _capture(lambda: shell.do_build(""))
        assert target.exists()
        assert shell.engine is not None
        assert shell.index is not None
        assert "Indexed" in out


class TestLoad:
    def test_load_with_missing_index_prints_friendly_message(
        self, shell_without_engine: Shell
    ) -> None:
        out = _capture(lambda: shell_without_engine.do_load(""))
        assert "No index found" in out
        assert shell_without_engine.engine is None

    def test_load_with_existing_index_sets_engine(self, tmp_path: Path) -> None:
        target = tmp_path / "saved.json"
        idx = _build_small_index()
        save_index(idx.to_dict(), target)
        shell = Shell(index_path=target)
        _capture(lambda: shell.do_load(""))
        assert shell.engine is not None
        assert shell.index is not None
        assert shell.index.document_count == 2

    def test_load_with_corrupt_file_prints_friendly_message(
        self, tmp_path: Path
    ) -> None:
        """If `load_index` succeeds but the JSON is not an index dict, we still print friendly."""
        target = tmp_path / "corrupt.json"
        target.write_text("\"not an index dict\"", encoding="utf-8")
        shell = Shell(index_path=target)
        out = _capture(lambda: shell.do_load(""))
        assert "Load failed" in out


class TestPrint:
    def test_print_before_load_prints_no_index_loaded(
        self, shell_without_engine: Shell
    ) -> None:
        out = _capture(lambda: shell_without_engine.do_print("cat"))
        assert "no index loaded" in out.lower()

    def test_print_with_valid_word_shows_posting_info(
        self, shell_with_engine: Shell
    ) -> None:
        out = _capture(lambda: shell_with_engine.do_print("cat"))
        assert "cat" in out
        assert "frequency" in out

    def test_print_with_empty_arg_prints_usage(
        self, shell_with_engine: Shell
    ) -> None:
        out = _capture(lambda: shell_with_engine.do_print(""))
        assert "usage" in out.lower()


class TestFind:
    def test_find_before_load_prints_no_index_loaded(
        self, shell_without_engine: Shell
    ) -> None:
        out = _capture(lambda: shell_without_engine.do_find("cat"))
        assert "no index loaded" in out.lower()

    def test_find_with_valid_query_prints_results(
        self, shell_with_engine: Shell
    ) -> None:
        out = _capture(lambda: shell_with_engine.do_find("cat"))
        assert "Found" in out
        assert "http://a.example.com/" in out

    def test_find_with_typo_offers_suggestions(
        self, shell_with_engine: Shell
    ) -> None:
        out = _capture(lambda: shell_with_engine.do_find("caat"))
        assert "did you mean" in out.lower()
        assert "cat" in out

    def test_find_with_ranking_flag_changes_engine(
        self, shell_with_engine: Shell
    ) -> None:
        """`--ranking bm25` should produce a Ranking: BM25 line in the output."""
        out_default = _capture(lambda: shell_with_engine.do_find("cat"))
        out_bm25 = _capture(
            lambda: shell_with_engine.do_find("--ranking bm25 cat")
        )
        assert "Ranking: TFIDF" in out_default
        assert "Ranking: BM25" in out_bm25

    def test_find_with_invalid_ranking_prints_usage(
        self, shell_with_engine: Shell
    ) -> None:
        out = _capture(
            lambda: shell_with_engine.do_find("--ranking bogus cat")
        )
        assert "Unknown ranking" in out

    def test_find_with_no_query_after_ranking_prints_usage(
        self, shell_with_engine: Shell
    ) -> None:
        out = _capture(
            lambda: shell_with_engine.do_find("--ranking bm25")
        )
        assert "Usage:" in out


class TestStats:
    def test_stats_prints_page_and_term_counts(
        self, shell_with_engine: Shell
    ) -> None:
        out = _capture(lambda: shell_with_engine.do_stats(""))
        assert "Pages:" in out
        assert "Terms:" in out
        assert "Top 10" in out


class TestUnknownCommand:
    def test_unknown_command_prints_help_hint(
        self, shell_without_engine: Shell
    ) -> None:
        out = _capture(
            lambda: shell_without_engine.default("frobnicate args")
        )
        assert "unknown command" in out.lower()
        assert "help" in out.lower()


class TestExtras:
    """Coverage-completing tests for trivial methods (benchmark, exit/quit/EOF, emptyline)."""

    def test_benchmark_prints_timing(
        self, shell_with_engine: Shell
    ) -> None:
        out = _capture(lambda: shell_with_engine.do_benchmark(""))
        assert "ms" in out
        assert "Benchmark" in out

    def test_exit_returns_true(self, shell_without_engine: Shell) -> None:
        result = shell_without_engine.do_exit("")
        assert result is True

    def test_quit_returns_true(self, shell_without_engine: Shell) -> None:
        result = shell_without_engine.do_quit("")
        assert result is True

    def test_eof_returns_true(self, shell_without_engine: Shell) -> None:
        result = shell_without_engine.do_EOF("")
        assert result is True

    def test_emptyline_returns_false(self, shell_without_engine: Shell) -> None:
        assert shell_without_engine.emptyline() is False
