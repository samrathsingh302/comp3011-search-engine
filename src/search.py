"""Search engine: AND intersection, TF-IDF and BM25 ranking, snippets.
See Lecture 12 (indexing) and Lecture 13 (query processing)."""

from __future__ import annotations

import difflib
import math
import re
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
        # Lazily cached on first BM25 call; see `_get_avg_doc_length`.
        self._avg_doc_length: float | None = None

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

    def _get_avg_doc_length(self) -> float:
        """Mean `word_count` across indexed documents, cached after first call.

        The cache is invalidation-free because the InvertedIndex is treated
        as immutable from the SearchEngine's point of view; rebuilding the
        engine after re-indexing is the supported path. Always returns at
        least 1.0 so the BM25 length-normalisation term cannot divide by
        zero on a freshly-constructed empty index.
        """
        if self._avg_doc_length is not None:
            return self._avg_doc_length
        word_counts = [
            int(doc.get("word_count", 0))
            for doc in self.index.documents.values()
        ]
        avg = sum(word_counts) / len(word_counts) if word_counts else 1.0
        self._avg_doc_length = max(1.0, avg)
        return self._avg_doc_length

    def _bm25_score(
        self,
        url: str,
        terms: list[str],
        posting_lists: dict[str, dict[str, dict[str, Any]]],
    ) -> float:
        """Okapi BM25 (Robertson and Walker 1994) with the +0.5 IDF smoothing.

        Formula per term: `idf(t) * tf * (k1 + 1) / (tf + k1 * (1 - b + b * dl / avgdl))`
        where `idf(t) = log(1 + (N - df + 0.5) / (df + 0.5))`. `k1` and `b` are
        the standard `BM25_K1 = 1.5` and `BM25_B = 0.75`. `dl` is the document
        length in tokens (we use `word_count` from the indexer-stored metadata).

        The +0.5 smoothing terms in the IDF numerator and denominator are part
        of the original paper and are essential: without them the IDF of a
        term that appears in every document goes negative, which would flip
        the sign of the contribution.
        """
        n_docs = max(1, self.index.document_count)
        avgdl = self._get_avg_doc_length()
        doc_len = max(
            1,
            int(self.index.documents.get(url, {}).get("word_count", 1)),
        )
        score = 0.0
        for term in terms:
            postings = posting_lists[term]
            df = len(postings)
            tf = int(postings[url].get("frequency", 0))
            idf = math.log(1 + (n_docs - df + 0.5) / (df + 0.5))
            numerator = tf * (BM25_K1 + 1)
            denominator = tf + BM25_K1 * (
                1 - BM25_B + BM25_B * doc_len / avgdl
            )
            score += idf * (numerator / denominator)
        return score

    def _tfidf_score(
        self,
        url: str,
        terms: list[str],
        posting_lists: dict[str, dict[str, dict[str, Any]]],
    ) -> float:
        """TF-IDF base score for `url` across the query `terms`.

        Smoothed IDF: `idf(t) = log((N + 1) / (df + 1)) + 1`. The `+1` on
        each side prevents `log(N/N) = 0` when every document contains the
        term (which would collapse the score to zero for queries dominated
        by common words), and the trailing `+ 1` keeps IDF strictly
        positive even on rare-everywhere corpora.
        """
        n_docs = max(1, self.index.document_count)
        score = 0.0
        for term in terms:
            postings = posting_lists[term]
            df = len(postings)
            tf = postings[url].get("frequency", 0)
            idf = math.log((n_docs + 1) / (df + 1)) + 1.0
            score += float(tf) * idf
        return score

    def _score_document(
        self,
        url: str,
        terms: list[str],
        posting_lists: dict[str, dict[str, dict[str, Any]]],
    ) -> float:
        """Dispatch on `self.ranking` and apply the title-field boost.

        The base ranking number comes from `_tfidf_score` (or, from Session
        3.1 onwards, `_bm25_score`). The title multiplier is then applied
        on top: a document whose title contains every query term gets the
        full `TITLE_BOOST` factor; partial title hits scale linearly.
        """
        if self.ranking == "tfidf":
            base = self._tfidf_score(url, terms, posting_lists)
        elif self.ranking == "bm25":
            base = self._bm25_score(url, terms, posting_lists)
        else:  # pragma: no cover - __init__ validation prevents this branch
            raise RuntimeError(f"unhandled ranking: {self.ranking}")

        title_hits = sum(
            1
            for term in terms
            if posting_lists[term][url].get("in_title", False)
        )
        title_multiplier = 1.0 + (TITLE_BOOST - 1.0) * (title_hits / len(terms))
        proximity_multiplier = self._proximity_boost(url, terms, posting_lists)
        return base * title_multiplier * proximity_multiplier

    def _proximity_boost(
        self,
        url: str,
        terms: list[str],
        posting_lists: dict[str, dict[str, dict[str, Any]]],
    ) -> float:
        """Proximity multiplier in `[1.0, 1.5]` based on how tightly query terms cluster.

        Single-term queries cannot have proximity, so they return `1.0`
        unconditionally. The document-wide span is computed across query
        terms (`max(last_position) - min(first_position)`); a span <= 0
        (all query terms at the same position) returns the maximum 1.5x.
        Otherwise the boost decays smoothly toward 1.0 as the span grows.
        """
        if len(terms) < 2:
            return 1.0

        first_positions: list[int] = []
        last_positions: list[int] = []
        for term in terms:
            positions = posting_lists[term][url].get("positions", [])
            if not positions:
                return 1.0
            first_positions.append(int(min(positions)))
            last_positions.append(int(max(positions)))

        span = max(last_positions) - min(first_positions)
        if span <= 0:
            return 1.5
        return 1.0 + min(0.5, 50.0 / (span + 50.0))

    def _make_snippet(
        self,
        url: str,
        terms: list[str],
        posting_lists: dict[str, dict[str, dict[str, Any]]],
    ) -> str:
        """Extract a `SNIPPET_WINDOW`-character window around the earliest matched term.

        Snippets are sliced from the per-document `body_excerpt` cached on
        the index in Session 2.2, not re-extracted from HTML. When the
        excerpt is empty or none of the query terms appear in it, falls
        back to the document title truncated to `SNIPPET_WINDOW`. Ellipsis
        prefixes/suffixes flag a mid-document window. Internal whitespace
        is collapsed so the snippet renders on a single line in the CLI.
        """
        doc = self.index.documents.get(url, {})
        excerpt: str = doc.get("body_excerpt", "")
        title: str = doc.get("title", "")

        if not excerpt:
            return title[:SNIPPET_WINDOW]

        lower = excerpt.lower()
        earliest = -1
        for term in terms:
            position = lower.find(term)
            if position != -1 and (earliest == -1 or position < earliest):
                earliest = position

        if earliest == -1:
            return title[:SNIPPET_WINDOW]

        half = SNIPPET_WINDOW // 2
        start = max(0, earliest - half)
        end = min(len(excerpt), start + SNIPPET_WINDOW)
        window = excerpt[start:end]

        if start > 0:
            window = "..." + window
        if end < len(excerpt):
            window = window + "..."

        return re.sub(r"\s+", " ", window).strip()

    def format_find_results(
        self, query: str, results: list[SearchResult]
    ) -> str:
        """Render the results of `find` for CLI display.

        Empty-query inputs return a brief usage line. Zero-match queries
        return a "No pages contain all of: ..." line and offer difflib
        suggestions for every query term that has no postings. Non-empty
        results are listed with URL, title, score, matched terms, and
        snippet on consecutive lines, with a leading "Ranking: ..." line
        so the user can tell which scorer produced the order.
        """
        if not results:
            terms = self.normalise_query(query)
            if not terms:
                return "Empty query. Try `find <words>`."
            lines = [f"No pages contain all of: {query}"]
            for term in terms:
                if not self.index.get_term(term):
                    close = self.suggest(term)
                    if close:
                        lines.append(
                            f"  {term}: did you mean {', '.join(close)}?"
                        )
            return "\n".join(lines)

        lines = [
            f"Found {len(results)} matching page(s) for: {query}",
            f"Ranking: {self.ranking.upper()}",
            "",
        ]
        for result in results:
            lines.append(f"  URL: {result.url}")
            if result.title:
                lines.append(f"  Title: {result.title}")
            lines.append(f"  Score: {result.score:.4f}")
            lines.append(f"  Matched: {', '.join(result.matched_terms)}")
            if result.snippet:
                lines.append(f"  Snippet: {result.snippet}")
            lines.append("")
        return "\n".join(lines).rstrip()

    def find(self, query: str, limit: int = 20) -> list[SearchResult]:
        """Conjunctive AND search across `query` terms.

        Lecture 13's shortest-list-first heuristic: posting lists are sorted
        by length and intersection proceeds from the shortest. Empty query
        or any term with no postings yields `[]`. Scoring goes through
        `_score_document`, which delegates to `_tfidf_score` and then
        applies the title-field boost.
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
            frequencies: dict[str, int] = {
                term: int(posting_lists[term][url].get("frequency", 0))
                for term in terms
            }
            score = self._score_document(url, terms, posting_lists)
            title = self.index.documents.get(url, {}).get("title", "")
            results.append(
                SearchResult(
                    url=url,
                    title=title,
                    score=score,
                    matched_terms=list(terms),
                    snippet=self._make_snippet(url, terms, posting_lists),
                    frequencies=frequencies,
                )
            )

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:limit]
