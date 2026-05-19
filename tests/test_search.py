"""Tests for src.search.SearchEngine."""

from __future__ import annotations

import pytest

from src.indexer import InvertedIndex
from src.search import SearchEngine, SearchResult


@pytest.fixture
def small_index() -> InvertedIndex:
    """Two-document in-memory corpus used by every test in this module."""
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
def engine(small_index: InvertedIndex) -> SearchEngine:
    return SearchEngine(small_index)


class TestPrintTerm:
    def test_print_term_returns_dict_for_known_word(self, engine: SearchEngine) -> None:
        entry = engine.print_term("cat")
        assert "http://a.example.com/" in entry
        assert "http://b.example.com/" in entry
        assert entry["http://a.example.com/"]["frequency"] == 2
        assert entry["http://b.example.com/"]["frequency"] == 1

    def test_print_term_returns_empty_dict_for_unknown(self, engine: SearchEngine) -> None:
        assert engine.print_term("zzzznonexistent") == {}


class TestFormatTermEntry:
    def test_format_term_entry_shows_posting_info(self, engine: SearchEngine) -> None:
        text = engine.format_term_entry("cat")
        assert "cat" in text
        assert "http://a.example.com/" in text
        assert "frequency" in text
        assert "in_title" in text

    def test_format_term_entry_offers_suggestions_on_miss(self, engine: SearchEngine) -> None:
        """`catz` is one edit away from indexed `cat` and `cats`; suggest must fire."""
        text = engine.format_term_entry("catz")
        assert "no postings" in text.lower()
        assert "did you mean" in text.lower()
        assert "cat" in text


class TestFind:
    def test_find_empty_query_returns_empty_list(self, engine: SearchEngine) -> None:
        assert engine.find("") == []
        assert engine.find("   ") == []

    def test_find_returns_empty_when_any_term_missing(self, engine: SearchEngine) -> None:
        # 'cat' is in both docs, 'zzzznonexistent' is in neither.
        assert engine.find("cat zzzznonexistent") == []

    def test_find_intersection_two_terms(self, engine: SearchEngine) -> None:
        """`cat dog` matches only doc A (cat is in both, dog only in A)."""
        results = engine.find("cat dog")
        assert len(results) == 1
        result = results[0]
        assert isinstance(result, SearchResult)
        assert result.url == "http://a.example.com/"
        # Sum of frequencies: freq(cat)=2 + freq(dog)=1 = 3
        assert result.score == 3.0
        assert set(result.matched_terms) == {"cat", "dog"}
        assert result.frequencies == {"cat": 2, "dog": 1}


class TestRanking:
    def test_find_invalid_ranking_raises_value_error(self, small_index: InvertedIndex) -> None:
        with pytest.raises(ValueError, match="Unknown ranking"):
            SearchEngine(small_index, ranking="bogus")

    def test_valid_rankings_accept_both_known_names(self, small_index: InvertedIndex) -> None:
        """Both `tfidf` and `bm25` must construct without raising; the scorer is identical for now."""
        assert SearchEngine(small_index, ranking="tfidf").ranking == "tfidf"
        assert SearchEngine(small_index, ranking="bm25").ranking == "bm25"
