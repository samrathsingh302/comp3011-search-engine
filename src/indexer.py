"""Indexer: tokenisation and inverted index. See Lecture 11 (tokenising edge cases) and Lecture 12 (extents, in_title field weighting)."""

from __future__ import annotations

import re
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
    except ImportError:
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
    """Return the visible page text with script, style, and noscript removed.

    Whitespace is collapsed to single spaces so that downstream position
    arithmetic in the indexer is not thrown off by HTML formatting noise.
    """
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator=" ")
    return re.sub(r"\s+", " ", text).strip()
