"""Indexer: tokenisation and inverted index. See Lecture 11 (tokenising edge cases) and Lecture 12 (extents, in_title field weighting)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from bs4 import BeautifulSoup

TOKEN_PATTERN = re.compile(r"[a-z0-9]+(?:['\-][a-z0-9]+)*", flags=re.UNICODE)

DEFAULT_STOPWORDS: frozenset[str] = frozenset({
    "the", "a", "an", "and", "or", "but", "of", "to", "in", "on", "at",
    "is", "are", "was", "were", "be", "by", "for", "with", "as",
    "this", "that", "it", "its", "from",
})

TITLE_BODY_POSITION_GAP = 1000

BODY_EXCERPT_CHARS = 2000


_UNICODE_TO_ASCII_PUNCTUATION = str.maketrans({
    "’": "'",  # right single quotation mark
    "‘": "'",  # left single quotation mark
    "ʼ": "'",  # modifier letter apostrophe
    "–": "-",  # en dash
    "—": "-",  # em dash
    "−": "-",  # minus sign
})


_porter_stemmer: Any = None
_stemmer_initialised: bool = False


def _normalise_unicode_punctuation(text: str) -> str:
    """Replace Unicode apostrophe and dash variants with ASCII equivalents.

    Real-world web text uses smart quotes and typographic dashes everywhere.
    Without this normalisation, `it’s` tokenises to `["it", "s"]` because
    `TOKEN_PATTERN` only recognises ASCII `'` and `-` as word-internal
    connectors. Lecture 11 calls out exactly this pitfall.
    """
    return text.translate(_UNICODE_TO_ASCII_PUNCTUATION)


def _get_porter_stemmer() -> Any:
    """Return a cached `PorterStemmer` instance, or `None` if nltk is absent.

    The import is lazy because pulling in nltk costs ~300 ms on a cold start
    and we only need it when a caller opts into stemming. On `ImportError`
    the function returns `None` so callers can degrade gracefully instead
    of crashing the whole pipeline.
    """
    global _porter_stemmer, _stemmer_initialised
    if _stemmer_initialised:
        return _porter_stemmer
    _stemmer_initialised = True
    try:
        from nltk.stem import PorterStemmer
    except ImportError:  # pragma: no cover - nltk is a required runtime dep
        _porter_stemmer = None
        return None
    _porter_stemmer = PorterStemmer()
    return _porter_stemmer


def tokenize(
    text: str,
    *,
    stem: bool = False,
    remove_stopwords: bool = False,
    stopwords: frozenset[str] | None = None,
) -> list[str]:
    """Split `text` into lowercase tokens, applying the Lecture 11 edge cases.

    Pipeline:
    1. Replace Unicode quote and dash variants with ASCII (smart quotes, en/em dashes).
    2. Lowercase the entire string (case-folding is global, not per-token).
    3. `TOKEN_PATTERN.findall`, which preserves word-internal apostrophes and
       hyphens (`don't`, `t-shirt`) but strips any leading/trailing ones.
    4. Optional stopword filter against `stopwords` or `DEFAULT_STOPWORDS`.
    5. Optional Porter stemming. If nltk is not installed the stemmer step
       silently no-ops rather than raising.

    `remove_stopwords` and `stem` are keyword-only to keep call sites readable.
    """
    if not text:
        return []
    normalised = _normalise_unicode_punctuation(text).lower()
    tokens: list[str] = TOKEN_PATTERN.findall(normalised)
    if remove_stopwords:
        active = stopwords if stopwords is not None else DEFAULT_STOPWORDS
        tokens = [t for t in tokens if t not in active]
    if stem:
        stemmer = _get_porter_stemmer()
        if stemmer is not None:
            tokens = [stemmer.stem(t) for t in tokens]
    return tokens


def extract_title(html: str) -> str:
    """Return the `<title>` element's text stripped of surrounding whitespace.

    An empty string is returned when the document has no `<title>`, a title
    element with empty content, or unparseable HTML.
    """
    soup = BeautifulSoup(html, "html.parser")
    title_tag = soup.title
    if title_tag is None or title_tag.string is None:
        return ""
    return title_tag.string.strip()


def extract_visible_text(html: str) -> str:
    """Return the visible page text with script, style, noscript, and head removed.

    The `<head>` is stripped because `BeautifulSoup.get_text()` otherwise
    includes `<title>` and meta-tag text in the body output, which would
    double-count title terms when the indexer combines title and body
    tokens at distinct position ranges. Whitespace is collapsed to single
    spaces so downstream position arithmetic is not thrown off by HTML
    formatting noise.
    """
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "head"]):
        tag.decompose()
    text = soup.get_text(separator=" ")
    return re.sub(r"\s+", " ", text).strip()


@dataclass
class IndexerOptions:
    """Knobs that change how `InvertedIndex.add_document` tokenises and lays out positions."""

    stem: bool = False
    remove_stopwords: bool = False
    title_position_gap: int = TITLE_BODY_POSITION_GAP


class InvertedIndex:
    """Positional inverted index with title/body field separation.

    Schema:
        index[term][url] = {
            "frequency": int,
            "positions": list[int],
            "in_title": bool,
        }
        documents[url] = {
            "title": str,
            "word_count": int,
            "fetched_at": str,   # ISO-8601 UTC timestamp
            "body_excerpt": str,  # <= BODY_EXCERPT_CHARS chars
        }

    Title tokens occupy positions `[0, len(title_tokens))`. Body tokens
    occupy `[title_position_gap, title_position_gap + len(body_tokens))`.
    The default gap (1000) is wider than any plausible title, so proximity
    boosts in the ranker cannot accidentally span the title/body boundary
    (Lecture 12 fields and extents).
    """

    def __init__(self, options: IndexerOptions | None = None) -> None:
        self.options: IndexerOptions = options or IndexerOptions()
        self.index: dict[str, dict[str, dict[str, Any]]] = {}
        self.documents: dict[str, dict[str, Any]] = {}

    def add_document(self, url: str, html: str) -> None:
        """Tokenise `html` and merge its terms, positions, and metadata into the index."""
        title_text = extract_title(html)
        body_text = extract_visible_text(html)

        title_tokens = tokenize(
            title_text,
            stem=self.options.stem,
            remove_stopwords=self.options.remove_stopwords,
        )
        body_tokens = tokenize(
            body_text,
            stem=self.options.stem,
            remove_stopwords=self.options.remove_stopwords,
        )

        for i, term in enumerate(title_tokens):
            self._add_occurrence(term, url, i, in_title=True)

        gap = self.options.title_position_gap
        for j, term in enumerate(body_tokens):
            self._add_occurrence(term, url, gap + j, in_title=False)

        self.documents[url] = {
            "title": title_text,
            "word_count": len(title_tokens) + len(body_tokens),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "body_excerpt": body_text[:BODY_EXCERPT_CHARS],
        }

    def _add_occurrence(
        self, term: str, url: str, position: int, *, in_title: bool
    ) -> None:
        """Append one occurrence to the posting list, promoting `in_title` to True if applicable."""
        postings = self.index.setdefault(term, {})
        entry: dict[str, Any] = postings.setdefault(
            url, {"frequency": 0, "positions": [], "in_title": False}
        )
        entry["frequency"] += 1
        entry["positions"].append(position)
        if in_title:
            entry["in_title"] = True

    def build_from_pages(self, pages: dict[str, str]) -> None:
        """Add every `(url, html)` pair via `add_document`."""
        for url, html in pages.items():
            self.add_document(url, html)

    def get_term(self, word: str) -> dict[str, dict[str, Any]]:
        """Look up `word` in the index, returning the per-URL posting dict or `{}`.

        The lookup is case-insensitive and Unicode-normalised so that callers
        do not need to pre-process query terms. If `options.stem` is True the
        same Porter step that ran during indexing is applied before lookup.
        """
        if not word:
            return {}
        normalised = _normalise_unicode_punctuation(word).lower()
        if self.options.stem:
            stemmer = _get_porter_stemmer()
            if stemmer is not None:
                normalised = stemmer.stem(normalised)
        return self.index.get(normalised, {})

    @property
    def vocabulary(self) -> list[str]:
        """Return every indexed term in sorted order."""
        return sorted(self.index.keys())

    @property
    def document_count(self) -> int:
        return len(self.documents)

    @property
    def term_count(self) -> int:
        return len(self.index)

    def to_dict(self) -> dict[str, Any]:
        """Serialise the index into a JSON-safe dict.

        The returned shape is:
            {
                "metadata": {"version", "term_count", "document_count", "options"},
                "documents": self.documents,
                "index": self.index,
            }
        `version` is "1.0" so that future schema changes can be detected by
        `from_dict` if we ever need to migrate older saved indices.
        """
        return {
            "metadata": {
                "version": "1.0",
                "term_count": self.term_count,
                "document_count": self.document_count,
                "options": {
                    "stem": self.options.stem,
                    "remove_stopwords": self.options.remove_stopwords,
                    "title_position_gap": self.options.title_position_gap,
                },
            },
            "documents": self.documents,
            "index": self.index,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> InvertedIndex:
        """Rebuild an `InvertedIndex` from the dict returned by `to_dict`.

        Defensive against missing keys: a corrupted or partial dict yields an
        empty index with default options rather than raising. Options are
        restored from `data["metadata"]["options"]` when present so that a
        loaded index honours the same stemmer and stopword choices the
        builder used.
        """
        metadata = data.get("metadata", {})
        options_dict = metadata.get("options", {})
        options = IndexerOptions(
            stem=options_dict.get("stem", False),
            remove_stopwords=options_dict.get("remove_stopwords", False),
            title_position_gap=options_dict.get(
                "title_position_gap", TITLE_BODY_POSITION_GAP
            ),
        )
        instance = cls(options=options)
        instance.documents = data.get("documents", {})
        instance.index = data.get("index", {})
        return instance
