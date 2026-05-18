"""Shared pytest fixtures backed by the HTML files captured by `scripts/capture_fixtures.py`."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.indexer import InvertedIndex

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def index() -> InvertedIndex:
    """A fresh InvertedIndex per test, with default options."""
    return InvertedIndex()


@pytest.fixture
def fixture_html() -> dict[str, str]:
    """Load every `tests/fixtures/*.html` file keyed by its stem.

    A missing fixtures directory yields an empty dict so tests that do not
    rely on real HTML still collect and run cleanly.
    """
    if not FIXTURES_DIR.is_dir():
        return {}
    return {
        path.stem: path.read_text(encoding="utf-8")
        for path in sorted(FIXTURES_DIR.glob("*.html"))
    }


@pytest.fixture
def sample_pages(fixture_html: dict[str, str]) -> dict[str, str]:
    """Map plausible URLs onto fixture HTML for the indexer and integration tests."""
    return {
        f"https://quotes.toscrape.com/page/{i}/": fixture_html[f"page{i}"]
        for i in (1, 2, 3)
        if f"page{i}" in fixture_html
    }
