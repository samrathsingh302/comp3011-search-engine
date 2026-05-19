"""Tests for src.search.SearchEngine."""

from __future__ import annotations

import pytest

from src.indexer import InvertedIndex
from src.search import SNIPPET_WINDOW, SearchEngine, SearchResult


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


class TestBm25:
    def test_bm25_scores_differ_from_tfidf(self, small_index: InvertedIndex) -> None:
        """TF-IDF and BM25 use different formulas; same query must yield different scores."""
        tfidf_engine = SearchEngine(small_index, ranking="tfidf")
        bm25_engine = SearchEngine(small_index, ranking="bm25")
        tfidf_results = tfidf_engine.find("cat")
        bm25_results = bm25_engine.find("cat")
        # Same set of matching URLs
        assert {r.url for r in tfidf_results} == {r.url for r in bm25_results}
        # But the score numbers diverge under different formulas
        tfidf_top = max(r.score for r in tfidf_results)
        bm25_top = max(r.score for r in bm25_results)
        assert tfidf_top != pytest.approx(bm25_top, rel=1e-6)

    def test_bm25_length_normalises(self) -> None:
        """At equal tf, BM25 ranks the shorter document above the longer one."""
        idx = InvertedIndex()
        idx.add_document(
            "http://short/",
            "<html><body>cat</body></html>",
        )
        long_filler = " ".join(["filler"] * 200)
        idx.add_document(
            "http://long/",
            f"<html><body>cat {long_filler}</body></html>",
        )
        engine = SearchEngine(idx, ranking="bm25")
        results = engine.find("cat")
        assert len(results) == 2
        short_score = next(r.score for r in results if r.url == "http://short/")
        long_score = next(r.score for r in results if r.url == "http://long/")
        assert short_score > long_score

    def test_avg_doc_length_is_cached(self, small_index: InvertedIndex) -> None:
        """`_get_avg_doc_length` memoises after the first call.

        Mutate the underlying documents after caching and confirm the cached
        value sticks. (Mutating the index after engine construction is not a
        supported path in production; this test asserts the cache, not policy.)
        """
        engine = SearchEngine(small_index, ranking="bm25")
        first = engine._get_avg_doc_length()
        small_index.documents["http://injected/"] = {
            "word_count": 999_999,
            "title": "x",
            "fetched_at": "2026-05-19T00:00:00+00:00",
            "body_excerpt": "",
        }
        second = engine._get_avg_doc_length()
        assert second == first

    def test_switching_ranking_changes_engine_behaviour(self, small_index: InvertedIndex) -> None:
        """A given query produces different per-document scores under tfidf vs bm25."""
        tfidf_engine = SearchEngine(small_index, ranking="tfidf")
        bm25_engine = SearchEngine(small_index, ranking="bm25")
        assert tfidf_engine.ranking == "tfidf"
        assert bm25_engine.ranking == "bm25"
        tfidf_scores = {r.url: r.score for r in tfidf_engine.find("cat")}
        bm25_scores = {r.url: r.score for r in bm25_engine.find("cat")}
        assert set(tfidf_scores) == set(bm25_scores)
        # At least one URL has different scores under the two rankings
        assert any(
            tfidf_scores[url] != pytest.approx(bm25_scores[url], rel=1e-6)
            for url in tfidf_scores
        )


class TestProximity:
    def test_proximity_boost_rewards_close_terms(self) -> None:
        """At equal TF, the doc with adjacent query terms ranks above the spread-out one."""
        idx = InvertedIndex()
        idx.add_document(
            "http://close/",
            "<html><body>cat dog</body></html>",
        )
        spread = " ".join(["filler"] * 1000)
        idx.add_document(
            "http://far/",
            f"<html><body>cat {spread} dog</body></html>",
        )
        engine = SearchEngine(idx)
        results = engine.find("cat dog")
        assert len(results) == 2
        close_score = next(r.score for r in results if r.url == "http://close/")
        far_score = next(r.score for r in results if r.url == "http://far/")
        assert close_score > far_score

    def test_proximity_returns_one_for_single_term_query(self, engine: SearchEngine) -> None:
        """A single-term query has no proximity to speak of; multiplier must be exactly 1.0."""
        posting_lists = {
            "cat": {"http://example.com/": {"positions": [1000]}},
        }
        assert engine._proximity_boost("http://example.com/", ["cat"], posting_lists) == 1.0


class TestSuggest:
    def test_suggest_returns_similar_words(self, engine: SearchEngine) -> None:
        """`caat` is one edit from indexed `cat`; suggest must surface it."""
        suggestions = engine.suggest("caat")
        assert "cat" in suggestions

    def test_suggest_returns_empty_for_unknown_words(self, engine: SearchEngine) -> None:
        """A token with no neighbours in the vocab must yield an empty list, not None."""
        assert engine.suggest("xyzqwertyabc") == []


class TestSnippet:
    def test_snippet_contains_matched_term_in_context(self) -> None:
        idx = InvertedIndex()
        body = (
            "Many animals live in zoos around the world. "
            "The elephant is one of the largest land creatures alive today. "
            "Some can live for over fifty years in the wild."
        )
        idx.add_document(
            "http://example.com/",
            f"<html><body>{body}</body></html>",
        )
        engine = SearchEngine(idx)
        results = engine.find("elephant")
        assert len(results) == 1
        snippet = results[0].snippet
        assert "elephant" in snippet.lower()
        # Window of 160 chars + up to 6 chars of ellipsis padding
        assert len(snippet) <= SNIPPET_WINDOW + 6

    def test_snippet_truncates_with_ellipsis_when_window_is_mid_document(self) -> None:
        idx = InvertedIndex()
        prefix = "lorem ipsum " * 80   # roughly 960 chars before the match
        suffix = "more text follows " * 40  # roughly 720 chars after the match
        body = f"{prefix} elephant {suffix}"
        idx.add_document(
            "http://example.com/",
            f"<html><body>{body}</body></html>",
        )
        engine = SearchEngine(idx)
        results = engine.find("elephant")
        snippet = results[0].snippet
        assert snippet.startswith("...")
        assert snippet.endswith("...")

    def test_snippet_falls_back_to_title_when_excerpt_empty(self) -> None:
        """A page with a title but no body should snippet-fall-back to the title."""
        idx = InvertedIndex()
        idx.add_document(
            "http://title-only/",
            "<html><head><title>Elephant Adventures</title></head><body></body></html>",
        )
        engine = SearchEngine(idx)
        results = engine.find("elephant")
        assert len(results) == 1
        assert "Elephant" in results[0].snippet


class TestFormatFindResults:
    def test_format_find_results_offers_suggestions_for_typo(self, engine: SearchEngine) -> None:
        """A typo with no postings should produce a `did you mean: ...` line."""
        results = engine.find("caat")
        formatted = engine.format_find_results("caat", results)
        assert "caat" in formatted
        assert "did you mean" in formatted.lower()
        assert "cat" in formatted

    def test_format_find_results_displays_hits(self, engine: SearchEngine) -> None:
        results = engine.find("cat")
        formatted = engine.format_find_results("cat", results)
        assert "Found" in formatted
        assert "Ranking: TFIDF" in formatted
        assert "http://a.example.com/" in formatted

    def test_format_find_results_empty_query_shows_usage(self, engine: SearchEngine) -> None:
        formatted = engine.format_find_results("", [])
        assert "empty query" in formatted.lower()
