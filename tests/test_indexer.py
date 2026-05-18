"""Tests for src.indexer tokeniser and HTML helpers."""

from __future__ import annotations

from src.indexer import (
    DEFAULT_STOPWORDS,
    extract_title,
    extract_visible_text,
    tokenize,
)


class TestTokenize:
    def test_tokenize_lowercases_input(self) -> None:
        assert tokenize("Hello World") == ["hello", "world"]

    def test_tokenize_strips_punctuation(self) -> None:
        assert tokenize("Hello, world! How are you?") == [
            "hello", "world", "how", "are", "you",
        ]

    def test_tokenize_keeps_apostrophes_inside_words(self) -> None:
        assert tokenize("don't won't master's") == ["don't", "won't", "master's"]

    def test_tokenize_keeps_hyphens_inside_words(self) -> None:
        assert tokenize("t-shirt e-bay state-of-the-art") == [
            "t-shirt", "e-bay", "state-of-the-art",
        ]

    def test_tokenize_handles_numbers(self) -> None:
        assert tokenize("Nokia 3250 model, version 92.3") == [
            "nokia", "3250", "model", "version", "92", "3",
        ]

    def test_tokenize_empty_input_returns_empty_list(self) -> None:
        assert tokenize("") == []

    def test_tokenize_handles_unicode_smart_quote(self) -> None:
        """U+2019 right single quotation mark should normalise to ASCII apostrophe."""
        assert tokenize("it’s mine") == ["it's", "mine"]

    def test_tokenize_with_stopword_removal(self) -> None:
        result = tokenize("the quick brown fox", remove_stopwords=True)
        assert "the" not in result
        assert result == ["quick", "brown", "fox"]

    def test_tokenize_without_stopword_removal_by_default(self) -> None:
        result = tokenize("the quick brown fox")
        assert "the" in result
        assert result == ["the", "quick", "brown", "fox"]

    def test_tokenize_with_porter_stemmer(self) -> None:
        """Porter reduces `running` and `runs` to the stem `run`."""
        result = tokenize("running runs", stem=True)
        assert result == ["run", "run"]

    def test_default_stopwords_contains_common_function_words(self) -> None:
        """Sanity check on the curated DEFAULT_STOPWORDS set."""
        for word in ("the", "a", "an", "and", "of", "to", "in", "is"):
            assert word in DEFAULT_STOPWORDS


class TestExtractTitle:
    def test_extract_title_basic(self) -> None:
        html = "<html><head><title>  Quotes to Scrape  </title></head><body></body></html>"
        assert extract_title(html) == "Quotes to Scrape"

    def test_extract_title_missing(self) -> None:
        html = "<html><body><p>no title element here</p></body></html>"
        assert extract_title(html) == ""


class TestExtractVisibleText:
    def test_extract_visible_text_strips_scripts(self) -> None:
        html = (
            "<html><body>"
            "<p>Hello</p>"
            "<script>alert('xss')</script>"
            "<style>.h { color: red; }</style>"
            "<noscript>fallback content</noscript>"
            "<p>World</p>"
            "</body></html>"
        )
        result = extract_visible_text(html)
        assert "Hello" in result
        assert "World" in result
        assert "alert" not in result
        assert "xss" not in result
        assert "color" not in result
        assert "fallback" not in result
