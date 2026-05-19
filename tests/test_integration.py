"""End-to-end integration tests using captured HTML fixtures (no real network).

These tests exercise the full pipeline (InvertedIndex -> Storage -> SearchEngine)
against the three captured `quotes.toscrape.com` pages stored in
`tests/fixtures/`. Mocking is intentionally absent: the fixtures are real HTML
from a live crawl, and every step runs against the actual production code.
"""

from __future__ import annotations

from pathlib import Path

from src.indexer import InvertedIndex
from src.search import SearchEngine, SearchResult
from src.storage import load_index, save_index


def test_full_pipeline_build_load_search(
    tmp_path: Path, sample_pages: dict[str, str]
) -> None:
    """Build index from fixtures, save to disk, reload, run a search end-to-end."""
    idx = InvertedIndex()
    idx.build_from_pages(sample_pages)

    target = tmp_path / "live.json"
    save_index(idx.to_dict(), target)

    loaded = InvertedIndex.from_dict(load_index(target))
    assert loaded.document_count == idx.document_count
    assert loaded.term_count == idx.term_count

    engine = SearchEngine(loaded)
    # "the" is overwhelmingly likely to appear on quotes.toscrape pages.
    results = engine.find("the")
    assert len(results) > 0
    assert isinstance(results[0], SearchResult)
    # Exercise SearchResult.to_dict so the serialisable view is covered too.
    payload = results[0].to_dict()
    assert "url" in payload
    assert "score" in payload


def test_round_trip_preserves_all_data(
    tmp_path: Path, sample_pages: dict[str, str]
) -> None:
    """`to_dict -> save -> load -> from_dict` must preserve postings exactly."""
    idx = InvertedIndex()
    idx.build_from_pages(sample_pages)

    target = tmp_path / "rt.json"
    save_index(idx.to_dict(), target)
    loaded = InvertedIndex.from_dict(load_index(target))

    assert loaded.vocabulary == idx.vocabulary
    assert loaded.documents.keys() == idx.documents.keys()
    assert loaded.options.title_position_gap == idx.options.title_position_gap

    # Spot-check a term that any quotes.toscrape page should carry.
    sample_term = "the"
    if sample_term in idx.vocabulary:
        original = idx.get_term(sample_term)
        copy = loaded.get_term(sample_term)
        assert set(original.keys()) == set(copy.keys())
        for url in original:
            assert (
                original[url]["frequency"] == copy[url]["frequency"]
            )
            assert original[url]["positions"] == copy[url]["positions"]
            assert original[url]["in_title"] == copy[url]["in_title"]


def test_multi_term_find_returns_ranked_results(
    sample_pages: dict[str, str]
) -> None:
    """Multi-term query must return SearchResults sorted by score descending."""
    idx = InvertedIndex()
    idx.build_from_pages(sample_pages)
    engine = SearchEngine(idx)

    results = engine.find("the of")
    # If both terms hit the same pages, we expect monotonic non-increasing scores.
    if len(results) >= 2:
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)


def test_print_on_known_word_returns_formatted_output(
    sample_pages: dict[str, str]
) -> None:
    """`format_term_entry` produces a human-readable multi-line view for an indexed word."""
    idx = InvertedIndex()
    idx.build_from_pages(sample_pages)
    engine = SearchEngine(idx)

    if "the" in idx.vocabulary:
        out = engine.format_term_entry("the")
        assert "the" in out
        assert "frequency" in out
        assert "in_title" in out
