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
        # Score is TF-IDF as of Session 2.6; we don't pin the exact number
        # here (a dedicated test in TestTfIdf does that) but it must be
        # strictly positive when both terms hit.
        assert result.score > 0
        assert set(result.matched_terms) == {"cat", "dog"}
        assert result.frequencies == {"cat": 2, "dog": 1}


class TestRanking:
    def test_find_invalid_ranking_raises_value_error(self, small_index: InvertedIndex) -> None:
        with pytest.raises(ValueError, match="Unknown ranking"):
            SearchEngine(small_index, ranking="bogus")

    def test_invalid_ranking_still_raises(self, small_index: InvertedIndex) -> None:
        """Regression check that the 2.6 scoring refactor did not loosen __init__ validation."""
        with pytest.raises(ValueError):
            SearchEngine(small_index, ranking="not_a_thing")

    def test_valid_rankings_accept_both_known_names(self, small_index: InvertedIndex) -> None:
        """Both `tfidf` and `bm25` must construct without raising."""
        assert SearchEngine(small_index, ranking="tfidf").ranking == "tfidf"
        assert SearchEngine(small_index, ranking="bm25").ranking == "bm25"

    def test_bm25_find_raises_not_implemented_until_3_1(self, small_index: InvertedIndex) -> None:
        """Until Session 3.1 lands BM25, calling find() with ranking=bm25 must raise loudly."""
        engine = SearchEngine(small_index, ranking="bm25")
        with pytest.raises(NotImplementedError, match="Session 3.1"):
            engine.find("cat")


class TestTfIdf:
    def test_tfidf_higher_for_more_frequent_term(self, engine: SearchEngine) -> None:
        """Doc A has cat with frequency 2; doc B has it once. A must rank above B."""
        results = engine.find("cat")
        assert len(results) == 2
        assert results[0].url == "http://a.example.com/"
        assert results[0].score > results[1].score

    def test_tfidf_rare_term_higher_idf_than_common_term(self) -> None:
        """A term that appears in 1 of 3 docs out-scores one that appears in all 3 at equal tf."""
        idx = InvertedIndex()
        idx.add_document("http://a/", "<html><body>common rare</body></html>")
        idx.add_document("http://b/", "<html><body>common</body></html>")
        idx.add_document("http://c/", "<html><body>common</body></html>")
        engine = SearchEngine(idx)

        rare_results = engine.find("rare")
        common_results = engine.find("common")
        assert len(rare_results) == 1
        rare_score = rare_results[0].score
        common_at_a = next(r.score for r in common_results if r.url == "http://a/")
        # Both have tf=1 in doc A; rare has df=1 vs common df=3 → idf_rare > idf_common.
        assert rare_score > common_at_a

    def test_title_hit_outranks_body_only_at_equal_tf(self) -> None:
        """Title containing the query term applies the TITLE_BOOST multiplier."""
        idx = InvertedIndex()
        idx.add_document(
            "http://title-hit/",
            "<html><head><title>cat</title></head><body>dummy</body></html>",
        )
        idx.add_document(
            "http://body-only/",
            "<html><body>cat</body></html>",
        )
        engine = SearchEngine(idx)

        results = engine.find("cat")
        assert len(results) == 2
        assert results[0].url == "http://title-hit/"
        # With both at tf=1, df=2, the title-hit score must be roughly 2.0x the body-only score.
        assert results[0].score == pytest.approx(2.0 * results[1].score, rel=0.01)
