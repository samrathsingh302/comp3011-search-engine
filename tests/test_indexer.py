"""Tests for src.indexer tokeniser, HTML helpers, and InvertedIndex."""

from __future__ import annotations

from src.indexer import (
    BODY_EXCERPT_CHARS,
    DEFAULT_STOPWORDS,
    InvertedIndex,
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

    def test_extract_visible_text_strips_styles(self) -> None:
        """Targeted test for the <style> branch; CSS declarations must not leak into output."""
        html = "<html><body><p>Hello</p><style>.h { color: red; font-weight: bold; }</style></body></html>"
        result = extract_visible_text(html)
        assert "Hello" in result
        assert "color" not in result
        assert "font-weight" not in result


class TestDefaultStopwords:
    def test_default_stopwords_contains_common_words(self) -> None:
        """Sanity check that DEFAULT_STOPWORDS includes the closed-class function words from Lecture 11."""
        for word in ("the", "a", "an", "and", "or", "of", "to", "in", "is", "it"):
            assert word in DEFAULT_STOPWORDS


class TestInvertedIndex:
    def test_add_single_document(self, index: InvertedIndex) -> None:
        html = "<html><head><title>Hello</title></head><body><p>world</p></body></html>"
        index.add_document("http://example.com/", html)
        assert index.document_count == 1
        assert "hello" in index.vocabulary
        assert "world" in index.vocabulary

    def test_index_stores_frequencies(self, index: InvertedIndex) -> None:
        html = "<html><body>cat cat dog</body></html>"
        index.add_document("http://example.com/", html)
        cat_postings = index.get_term("cat")
        assert cat_postings["http://example.com/"]["frequency"] == 2
        assert index.get_term("dog")["http://example.com/"]["frequency"] == 1

    def test_index_stores_positions(self, index: InvertedIndex) -> None:
        """Body positions start at the title-vs-body gap (default 1000)."""
        html = "<html><body>alpha beta gamma</body></html>"
        index.add_document("http://example.com/", html)
        beta_positions = index.get_term("beta")["http://example.com/"]["positions"]
        assert beta_positions == [1001]

    def test_index_separates_title_and_body_positions(self, index: InvertedIndex) -> None:
        html = "<html><head><title>quick fox</title></head><body>jumped over</body></html>"
        index.add_document("http://example.com/", html)
        quick = index.get_term("quick")["http://example.com/"]
        jumped = index.get_term("jumped")["http://example.com/"]
        assert quick["positions"] == [0]
        assert jumped["positions"][0] >= 1000

    def test_index_marks_in_title_flag(self, index: InvertedIndex) -> None:
        html = "<html><head><title>Python</title></head><body>java</body></html>"
        index.add_document("http://example.com/", html)
        assert index.get_term("python")["http://example.com/"]["in_title"] is True
        assert index.get_term("java")["http://example.com/"]["in_title"] is False

    def test_index_is_case_insensitive(self, index: InvertedIndex) -> None:
        html = "<html><body>HELLO hello Hello</body></html>"
        index.add_document("http://example.com/", html)
        assert index.get_term("hello")["http://example.com/"]["frequency"] == 3
        assert index.get_term("HELLO")["http://example.com/"]["frequency"] == 3

    def test_missing_term_returns_empty_dict(self, index: InvertedIndex) -> None:
        index.add_document("http://example.com/", "<html><body>hello</body></html>")
        assert index.get_term("nonexistent") == {}

    def test_build_from_pages_handles_multiple_documents(self, index: InvertedIndex) -> None:
        pages = {
            "http://a.example.com/": "<html><body>alpha alpha beta</body></html>",
            "http://b.example.com/": "<html><body>beta gamma</body></html>",
        }
        index.build_from_pages(pages)
        assert index.document_count == 2
        alpha = index.get_term("alpha")
        beta = index.get_term("beta")
        assert "http://a.example.com/" in alpha
        assert "http://b.example.com/" not in alpha
        assert "http://a.example.com/" in beta
        assert "http://b.example.com/" in beta

    def test_vocabulary_is_sorted(self, index: InvertedIndex) -> None:
        index.add_document(
            "http://example.com/",
            "<html><body>zebra apple monkey banana</body></html>",
        )
        assert index.vocabulary == sorted(index.vocabulary)

    def test_documents_store_body_excerpt(self, index: InvertedIndex) -> None:
        html = "<html><body>some visible text here for snippet generation</body></html>"
        index.add_document("http://example.com/", html)
        excerpt = index.documents["http://example.com/"]["body_excerpt"]
        assert "visible" in excerpt

    def test_body_excerpt_is_truncated(self, index: InvertedIndex) -> None:
        """A document with >2000 chars of body must have its excerpt capped at BODY_EXCERPT_CHARS."""
        long_text = "lorem ipsum " * 300  # ~3600 chars after whitespace collapse
        html = f"<html><body><p>{long_text}</p></body></html>"
        index.add_document("http://example.com/", html)
        excerpt = index.documents["http://example.com/"]["body_excerpt"]
        assert len(excerpt) <= BODY_EXCERPT_CHARS
