"""Search engine: AND intersection, TF-IDF and BM25 ranking, snippets.
See Lecture 12 (indexing) and Lecture 13 (query processing)."""

from __future__ import annotations

import difflib
from dataclasses import dataclass, field
from typing import Any

from src.indexer import InvertedIndex, tokenize

BM25_K1 = 1.5
BM25_B = 0.75
TITLE_BOOST = 2.0
SNIPPET_WINDOW = 160

_VALID_RANKINGS = {"tfidf", "bm25"}


@dataclass
class SearchResult:
    """One hit returned by `SearchEngine.find`.

    `score` is the ranker's final number; higher is better. `frequencies`
    maps each matched query term to its in-document count, useful for the
    CLI's `print` view and for the snippet generator in Session 3.2.
    """

    url: str
    title: str
    score: float
    matched_terms: list[str]
    snippet: str = ""
    frequencies: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe dict representation of the result."""
        return {
            "url": self.url,
            "title": self.title,
            "score": self.score,
            "matched_terms": list(self.matched_terms),
            "snippet": self.snippet,
            "frequencies": dict(self.frequencies),
        }


class SearchEngine:
    """Ranked search over an `InvertedIndex`.

    Construction takes a built index and a ranking algorithm name
    (`"tfidf"` or `"bm25"`). The ranking switch is plumbed through from
    day one so the Session 3.3 `--ranking` CLI flag does not need a
    refactor; the actual TF-IDF / BM25 maths arrive in Sessions 2.6 and
    3.1 respectively. The current `find()` returns a plain
    sum-of-frequencies score so the AND-intersection plumbing is fully
    testable without depending on the not-yet-implemented ranker.
    """

    def __init__(self, index: InvertedIndex, ranking: str = "tfidf") -> None:
        if ranking not in _VALID_RANKINGS:
            raise ValueError(
                f"Unknown ranking {ranking!r}; expected one of "
                f"{sorted(_VALID_RANKINGS)}"
            )
        self.index = index
        self.ranking = ranking

    def normalise_query(self, query: str) -> list[str]:
        """Tokenise `query` with the same options the index was built with."""
        return tokenize(
            query,
            stem=self.index.options.stem,
            remove_stopwords=self.index.options.remove_stopwords,
        )

    def print_term(self, word: str) -> dict[str, dict[str, Any]]:
        """Return the posting dict for `word`, or `{}` if unknown."""
        return self.index.get_term(word)

    def format_term_entry(self, word: str) -> str:
        """Multi-line, human-readable view of a term's postings.

        When the term is unknown, returns a single line of "Term X has no
        postings" followed by a "Did you mean: ..." line if any close
        vocabulary matches exist.
        """
        entry = self.print_term(word)
        if not entry:
            suggestions = self.suggest(word)
            if suggestions:
                return (
                    f"Term {word!r} has no postings. "
                    f"Did you mean: {', '.join(suggestions)}?"
                )
            return f"Term {word!r} has no postings."

        lines = [f"Term {word!r} appears in {len(entry)} document(s):"]
        for url, posting in sorted(entry.items()):
            positions = posting.get("positions", [])
            shown = positions[:5]
            tail = (
                f" ... (+{len(positions) - 5} more)"
                if len(positions) > 5
                else ""
            )
            lines.append(
                f"  - {url}: frequency={posting.get('frequency', 0)}, "
                f"in_title={posting.get('in_title', False)}, "
                f"positions={shown}{tail}"
            )
        return "\n".join(lines)

    def suggest(self, word: str, n: int = 3) -> list[str]:
        """Return up to `n` close vocabulary matches for a misspelled query term."""
        return difflib.get_close_matches(
            word, self.index.vocabulary, n=n, cutoff=0.7
        )

    def find(self, query: str, limit: int = 20) -> list[SearchResult]:
        """Conjunctive AND search across `query` terms.

        Lecture 13's shortest-list-first heuristic: posting lists are sorted
        by length and intersection proceeds from the shortest. Empty query
        or any term with no postings yields `[]`. The current scorer is a
        plain sum of frequencies; TF-IDF arrives in Session 2.6 and BM25
        in Session 3.1.
        """
        raw_terms = self.normalise_query(query)
        if not raw_terms:
            return []

        # Dedup while preserving the user's term order, so identical query
        # tokens do not double-count in the score.
        seen: set[str] = set()
        terms: list[str] = []
        for term in raw_terms:
            if term not in seen:
                seen.add(term)
                terms.append(term)

        posting_lists: dict[str, dict[str, dict[str, Any]]] = {}
        for term in terms:
            postings = self.index.get_term(term)
            if not postings:
                return []
            posting_lists[term] = postings

        ordered_terms = sorted(terms, key=lambda t: len(posting_lists[t]))
        candidate_urls: set[str] = set(posting_lists[ordered_terms[0]].keys())
        for term in ordered_terms[1:]:
            candidate_urls &= set(posting_lists[term].keys())
            if not candidate_urls:
                return []

        results: list[SearchResult] = []
        for url in candidate_urls:
            frequencies: dict[str, int] = {}
            score = 0.0
            for term in terms:
                freq = int(posting_lists[term][url].get("frequency", 0))
                frequencies[term] = freq
                score += float(freq)
            title = self.index.documents.get(url, {}).get("title", "")
            results.append(
                SearchResult(
                    url=url,
                    title=title,
                    score=score,
                    matched_terms=list(terms),
                    snippet="",
                    frequencies=frequencies,
                )
            )

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:limit]
