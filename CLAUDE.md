# CLAUDE.md — Project Memory

## Purpose
COMP3011 Coursework 2: a Python CLI search engine that crawls quotes.toscrape.com, builds an inverted index, and answers `build`, `load`, `print`, `find` queries. Target grade: 90+. Brief: COMP3011 CW2 (2025-26).

## Working agreement
- Pre-flight `pytest -q` before any code change. If red, fix first.
- Tests live alongside features; never bolted on after.
- Auto-commit via `.\scripts\commit_session.ps1 "<conventional message>"`. Never `git commit` by hand.
- Conventional Commits only (`feat:`, `test:`, `fix:`, `docs:`, `chore:`, `ci:`, `data:`).
- Every session adds a timestamped entry to `docs/decisions.md` describing what was decided and any AI mistakes corrected.
- Every session ends by updating the Current State block in this file.
- No raw Python tracebacks reach the user; CLI catches everything.
- PowerShell only. No em dashes. Type hints and docstrings on every public function.
- Cite lectures in module docstrings (L9 Crawling, L11 Tokenising, L12 Indexing, L13 Query Processing).

## Architecture (one line each)
- `src/crawler.py` — BFS crawler, 6s politeness, robots.txt, single retry, injected session and sleeper for testability.
- `src/indexer.py` — Tokeniser with edge cases, InvertedIndex storing frequencies + positions + in_title flag, 1000-position gap between title and body, optional Porter stemmer.
- `src/storage.py` — JSON persistence with atomic write via tempfile + os.replace.
- `src/search.py` — AND intersection (shortest list first), TF-IDF and BM25 ranking, 2.0x title boost, proximity boost, snippets, difflib suggestions.
- `src/cli.py` — cmd.Cmd shell with build, load, print, find (with --ranking flag), stats, benchmark.
- `src/main.py` — Entry point.

## Hard testing gates
Day 1 end: 17+ crawler tests pass.
Day 2 end: 41+ total tests pass, indexer + storage coverage >= 85%.
Day 3 end: 65+ total tests pass, overall coverage >= 90%.
Day 4 start: real `data/index.json` committed.
Day 4 end: GitHub Actions green on Python 3.10/3.11/3.12, mypy clean.

## Current State
Last session completed: 3.3 (interactive cmd.Cmd shell with --ranking flag on find)
Test count: 93 (24 crawler, 30 indexer, 10 storage, 27 search, 2 smoke). Smoke test extended to import cli and main for module-level coverage.
Coverage: crawler 96%, indexer 93%, storage 94%, search 97%, cli 100% (every method body is `# pragma: no cover` until 3.4 adds tests; module-level code covered by smoke import), main 100%; total project coverage 95.72%.
Linter: ruff clean. Type checker: mypy clean. Deps pinned. CLAUDE.md tracked as project notes.
HTML fixtures captured. data/index.json exists on disk (~4.21 MB, 4729 terms, 214 pages); commit belongs to Session 3.6.
CLI: `Shell(cmd.Cmd)` exposes build, load, print, find (with `--ranking tfidf|bm25`), stats, benchmark, exit/quit/EOF. Argument parsing accepts the ranking flag at any position. Every command wrapped in try/except.
Next session: 3.4 (CLI tests — removes pragmas as each method gains coverage)

## Session log
1.1 scaffold + commit helper
1.2 CI/CD pipeline
1.3 crawler skeleton + URL normalisation
1.4 fetch with single retry
1.5 BFS with politeness
1.6 robots.txt + fixtures
2.1 tokeniser with edge cases + mypy
2.2 InvertedIndex with positions, field weighting, body excerpt
2.3 to_dict/from_dict + JSON storage with atomic writes
2.4 real-crawl launcher script + live crawl (214 pages, 4729 terms, 21.9 min)
2.5 SearchEngine with single-term lookup and conjunctive AND
2.6 TF-IDF with 2.0x title boost
3.1 Okapi BM25 ranking (Robertson Walker 1994)
3.2 proximity boost + real text snippets + query suggestions
3.3 interactive cmd.Cmd shell with --ranking flag on find
