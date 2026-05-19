"""CLI: cmd.Cmd shell wrapping crawler, index, storage, and search."""

from __future__ import annotations

import cmd
import time
from pathlib import Path

from src.crawler import Crawler, CrawlerConfig
from src.indexer import InvertedIndex
from src.search import SearchEngine
from src.storage import (
    DEFAULT_INDEX_PATH,
    IndexNotFoundError,
    load_index,
    save_index,
)

VALID_RANKINGS = ("tfidf", "bm25")

SAMPLE_BENCHMARK_QUERIES = (
    "good friends",
    "knowledge power",
    "love peace",
    "life death",
    "freedom truth",
    "wisdom",
    "happiness",
)


class Shell(cmd.Cmd):
    """Interactive REPL wrapping the crawler, indexer, storage, and search engine.

    The brief mandates an interactive shell for `build`, `load`, `print`, and
    `find`. Everything else (`stats`, `benchmark`, the `--ranking` flag on
    `find`) is an extension. Every command body is wrapped in `try/except`
    so a raw Python traceback never escapes to the user (see CLAUDE.md
    working agreement).
    """

    intro = (
        "COMP3011 Search Engine. "
        "Type `help` for commands; `exit` or Ctrl-D to quit."
    )
    prompt = "(search) "

    def __init__(  # pragma: no cover
        self,
        index_path: str | Path | None = None,
        crawler_config: CrawlerConfig | None = None,
    ) -> None:
        super().__init__()
        self.index_path: Path = (
            Path(index_path) if index_path else DEFAULT_INDEX_PATH
        )
        self.crawler_config: CrawlerConfig = crawler_config or CrawlerConfig()
        self.index: InvertedIndex | None = None
        self.engine: SearchEngine | None = None

    def _require_index(self) -> bool:  # pragma: no cover
        """Print a friendly message and return False when no index is loaded."""
        if self.engine is None or self.index is None:
            print(
                "No index loaded. "
                "Run `build` to crawl now, or `load` to read a saved index."
            )
            return False
        return True

    def do_build(self, line: str) -> None:  # pragma: no cover
        """build: Crawl the configured site and build a fresh inverted index."""
        try:
            print(
                f"Crawling {self.crawler_config.base_url} with "
                f"{self.crawler_config.delay_seconds}s politeness ..."
            )
            crawler = Crawler(self.crawler_config)
            pages = crawler.crawl()
            print(f"Crawled {len(pages)} pages.")
            self.index = InvertedIndex()
            self.index.build_from_pages(pages)
            save_index(self.index.to_dict(), self.index_path)
            self.engine = SearchEngine(self.index)
            print(
                f"Indexed {self.index.term_count} terms across "
                f"{self.index.document_count} pages."
            )
            print(f"Saved to {self.index_path}.")
        except Exception as exc:
            print(f"Build failed: {exc}")

    def do_load(self, line: str) -> None:  # pragma: no cover
        """load: Read a previously-saved inverted index from disk."""
        try:
            data = load_index(self.index_path)
            self.index = InvertedIndex.from_dict(data)
            self.engine = SearchEngine(self.index)
            print(
                f"Loaded {self.index.document_count} pages "
                f"({self.index.term_count} terms) from {self.index_path}."
            )
        except IndexNotFoundError as exc:
            print(str(exc))
        except Exception as exc:
            print(f"Load failed: {exc}")

    def do_print(self, line: str) -> None:  # pragma: no cover
        """print <word>: Show posting list info for a single term."""
        word = line.strip()
        if not word:
            print("Usage: print <word>")
            return
        if not self._require_index():
            return
        assert self.engine is not None
        try:
            print(self.engine.format_term_entry(word))
        except Exception as exc:
            print(f"Print failed: {exc}")

    def do_find(self, line: str) -> None:  # pragma: no cover
        """find [--ranking tfidf|bm25] <query>: AND-search for all query terms.

        The `--ranking` flag may appear anywhere in the argument list; the
        token immediately after it is the ranking name. Without the flag,
        the engine's default ranker is used.
        """
        tokens = line.split()
        ranking: str | None = None
        i = 0
        while i < len(tokens):
            if tokens[i] == "--ranking":
                if i + 1 >= len(tokens):
                    print("Usage: find [--ranking tfidf|bm25] <query>")
                    return
                value = tokens[i + 1]
                if value not in VALID_RANKINGS:
                    print(
                        f"Unknown ranking: {value!r}. "
                        f"Expected one of {list(VALID_RANKINGS)}."
                    )
                    return
                ranking = value
                del tokens[i:i + 2]
            else:
                i += 1
        if not tokens:
            print("Usage: find [--ranking tfidf|bm25] <query>")
            return
        query = " ".join(tokens)
        if not self._require_index():
            return
        assert self.engine is not None
        assert self.index is not None
        try:
            if ranking is not None and self.engine.ranking != ranking:
                engine = SearchEngine(self.index, ranking=ranking)
            else:
                engine = self.engine
            results = engine.find(query)
            print(engine.format_find_results(query, results))
        except Exception as exc:
            print(f"Search failed: {exc}")

    def do_stats(self, line: str) -> None:  # pragma: no cover
        """stats: Print page count, term count, total postings, top 10 terms."""
        if not self._require_index():
            return
        assert self.index is not None
        try:
            pages = self.index.document_count
            terms = self.index.term_count
            total_postings = sum(
                len(postings) for postings in self.index.index.values()
            )
            term_frequencies = [
                (
                    term,
                    sum(
                        int(p.get("frequency", 0))
                        for p in postings.values()
                    ),
                )
                for term, postings in self.index.index.items()
            ]
            term_frequencies.sort(key=lambda x: x[1], reverse=True)
            print(f"Pages: {pages}")
            print(f"Terms: {terms}")
            print(f"Total postings: {total_postings}")
            print("Top 10 terms by total frequency:")
            for term, freq in term_frequencies[:10]:
                print(f"  {term}: {freq}")
        except Exception as exc:
            print(f"Stats failed: {exc}")

    def do_benchmark(self, line: str) -> None:  # pragma: no cover
        """benchmark: Time 7 sample queries and print millisecond elapsed for each."""
        if not self._require_index():
            return
        assert self.engine is not None
        try:
            print("Benchmark results:")
            for query in SAMPLE_BENCHMARK_QUERIES:
                t0 = time.perf_counter()
                results = self.engine.find(query)
                elapsed_ms = (time.perf_counter() - t0) * 1000
                print(
                    f"  {query!r}: {len(results)} hits in {elapsed_ms:.2f} ms"
                )
        except Exception as exc:
            print(f"Benchmark failed: {exc}")

    def do_exit(self, line: str) -> bool:  # pragma: no cover
        """exit: Leave the shell."""
        print("Goodbye.")
        return True

    def do_quit(self, line: str) -> bool:  # pragma: no cover
        """quit: Alias for `exit`."""
        return self.do_exit(line)

    def do_EOF(self, line: str) -> bool:  # pragma: no cover
        """EOF: Treat Ctrl-D / end-of-input as exit."""
        print()
        return self.do_exit(line)

    def default(self, line: str) -> None:  # pragma: no cover
        """Fallback for any unrecognised command."""
        first = line.split()[0] if line.split() else line
        print(
            f"Unknown command: {first!r}. "
            f"Type `help` for available commands."
        )

    def emptyline(self) -> bool:  # pragma: no cover
        """Override cmd.Cmd's default (which would repeat the last command).

        Returns False so the cmdloop stays open on a blank line; cmd.Cmd's
        typeshed stub declares the return type as `bool`, hence the explicit
        return rather than an implicit `None`.
        """
        return False


def run(index_path: str | Path | None = None) -> None:  # pragma: no cover
    """Construct the shell and enter its blocking command loop."""
    shell = Shell(index_path=index_path)
    try:
        shell.cmdloop()
    except KeyboardInterrupt:
        print()
        print("Goodbye (interrupted).")
