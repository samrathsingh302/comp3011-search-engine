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
Last session completed: 4.4 (GitHub push verified; CI green on all three Python versions; v1.0-submission tag pushed)
Test count: 127. Coverage 100% on all src/ modules. ruff + mypy clean.
Repo: https://github.com/samrathsingh302/comp3011-search-engine (PUBLIC). Repo name differs from v7.1 spec's `comp3011-cw2`; the repo was created Day 1 under the more descriptive name and was kept rather than splitting history.
CI: run 26102490346 on commit 74b098c (== v1.0-submission tag) succeeded on Python 3.10 (24s), 3.11 (21s), 3.12 (20s).
Tags pushed: v0.2-crawler, v0.3-indexer-storage, v0.4-search, v0.5-cli, v0.9-tests-passing, v1.0-submission.
Postamble edits (decisions.md "## CI green ..." entry + this CLAUDE.md update) are staged uncommitted because the 4.4 spec did not call for `commit_session`; the v1.0-submission tag stays on the pre-postamble commit as the canonical submission marker. Future sessions can fold these edits in.
Next session: 4.5 (recording walkthrough)

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
3.4 CLI test suite with mocked Crawler and engine
3.5 end-to-end integration tests + coverage push to 100%
3.6 commit real index, manual sanity check, scale benchmark
4.1 comprehensive README with architecture, benchmarks, and ranking comparison
4.2 GenAI critical evaluation drawn from decisions log (14 verbatim AI-note events)
4.3 word-for-word video script (4:30 target) + demo_runner teleprompter
4.4 GitHub push, CI green on Python 3.10/3.11/3.12, v1.0-submission tag pushed
