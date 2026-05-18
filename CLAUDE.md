# CLAUDE.md — Project Memory

## Purpose
COMP3011 Coursework 2: a Python CLI search engine that crawls quotes.toscrape.com, builds an inverted index, and answers `build`, `load`, `print`, `find` queries. Target grade: 90+. Brief is in `$HOME\comp3011-reference\` for verification only; NEVER copy from it.

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

## Reference location (read-only)
`$HOME\comp3011-reference\` — fully working previous implementation. Use `Get-Content` to verify shapes when stuck. DO NOT copy.

## Hard testing gates
Day 1 end: 17+ crawler tests pass.
Day 2 end: 41+ total tests pass, indexer + storage coverage >= 85%.
Day 3 end: 65+ total tests pass, overall coverage >= 90%.
Day 4 start: real `data/index.json` committed.
Day 4 end: GitHub Actions green on Python 3.10/3.11/3.12, mypy clean.

## Current State
Last session completed: 1.4
Test count: 9
Coverage: not yet measured (only crawler tests so far)
Next session: 1.5 (BFS with politeness)

## Session log
1.1 scaffold + commit helper
1.2 CI/CD pipeline
1.3 crawler skeleton + URL normalisation
1.4 fetch with single retry
