# CLAUDE.md: Persistent Project Memory

Read this file at the start of every session. Update the **Current state** section at the end of every session.

## Project goal

COMP3011 Web Services and Web Data Coursework 2: a Python search engine that crawls `quotes.toscrape.com`, builds a positional inverted index, and serves ranked queries through an interactive shell. Target grade band 80 to 100 (excellent to outstanding), aiming for 90 or higher. The coursework brief is the source of truth for what to build. `$HOME\comp3011-reference\` is a verification oracle of shape and behaviour, never source material to copy.

## Reference project

- **Location:** `C:\Users\samra\comp3011-reference\`
- **Status:** READ-ONLY. Consult to verify API signatures, file shapes, and test patterns when in doubt. Never copy files wholesale and never paraphrase whole functions. If a file in `comp3011-cw2\` ends up structurally identical to its reference twin, rewrite it.
- **Why this matters:** the marker checks for plausible authorship and the GenAI evaluation declares the AI usage honestly. Every line must be one the student can explain.

## Working agreement

1. **Pre-flight first.** Every session begins by running `.\.venv\Scripts\pytest.exe -q` to confirm the previous state is green. If red, fix it before adding new code.
2. **Tests alongside features, never after.** No session ends without tests for new code.
3. **Auto-commit only.** End every session with `.\scripts\commit_session.ps1 "<conventional message>"`. The helper runs pytest, refuses to commit on red, then pushes to `origin/main`.
4. **No raw tracebacks** ever reach the user. Wrap user-facing entry points in clean error handling.
5. **Conventional Commits** for every commit: `feat`, `fix`, `test`, `docs`, `chore`, `ci`, `refactor`, `data`, `perf`.
6. **One session at a time.** Do only the session the user pastes. Stop at its DONE rule and wait.

## Architecture (10 lines)

1. **Crawler** (`src/crawler.py`): BFS from a seed URL, at least 6 s politeness, robots.txt with Crawl-delay respect, single retry on transient errors, injectable session and sleeper.
2. **Tokeniser** (`src/indexer.py::tokenize`): regex `[a-z0-9]+(?:['\-][a-z0-9]+)*` with unicode normalisation, optional Porter stemmer, optional stopword removal.
3. **InvertedIndex** (`src/indexer.py`): schema `index[term][url] = {frequency, positions, in_title}`. Body positions start at the title-vs-body gap of 1000 so proximity cannot cross the boundary.
4. **Storage** (`src/storage.py`): atomic JSON write to `data/index.json` via `tempfile.mkstemp` plus `os.replace`. `load_index` raises a friendly `IndexNotFoundError` when missing.
5. **SearchEngine** (`src/search.py`): AND intersection ordered shortest-list-first, TF-IDF or BM25 (Robertson and Walker 1994), 2.0x title boost, proximity boost capped at 1.5x.
6. **CLI Shell** (`src/cli.py`): `cmd.Cmd` REPL with `build`, `load`, `print`, `find`, `stats`, `benchmark`, `exit`. Every command is wrapped in try/except.
7. **Snippets** generated from stored positions, capped at 160 chars.
8. **Suggestions** via `difflib.get_close_matches` against the vocabulary when a query term misses.
9. **Tests** mock all HTTP and all sleep. CI matrix on Python 3.10, 3.11, 3.12. Coverage gate 85 percent, target 90 percent or higher.
10. **Entry point** `src/main.py` runs the shell. Invoke as `python -m src.main`.

## Hard rules

- **PowerShell only.** Use `python`, not `python3`. Chain commands with `;` (PowerShell 5.1 has no `&&`). Prefer `Set-Location`, `Get-Content`, `New-Item`, `Copy-Item` over POSIX equivalents.
- **No em dashes** in any file written to disk. Use commas, full stops, hyphens, or colons.
- **No editor opens.** Files are created and edited with the Write and Edit tools. Notepad, VSCode, and similar are never launched.
- **Lecture citations in module docstrings:** L9 (Web Crawling) in `crawler.py`. L11 (Parsing and Tokenisation) and L12 (Indexing) in `indexer.py`. L12 plus L13 (Query Processing) in `search.py`.
- **Type hints and docstrings** on every public function and class (80 to 100 marking band requirement).
- **No real network in tests.** Mock `requests.Session.get` and the sleeper everywhere. Real-network behaviour is exercised only when the user runs `build` themselves.
- **Commit helper auto-pushes** to `origin/main` after every green commit. Do not skip with `--no-verify`.

## Current state

<!-- UPDATE this section at the end of every session. -->

- **Last session completed:** Session 1.3 (crawler config, URL normalisation, scope check)
- **Last commit:** `4c5ae93 feat(crawler): add config, URL normalisation, and scope check`
- **Tests passing:** 13 (2 smoke, 11 crawler)
- **Coverage:** 100 percent (`src/crawler.py` 39/39, `src/__init__.py` 0/0)
- **Next session:** **Session 1.4** add `Crawler._fetch` with single retry on transient `requests.RequestException`, 1 s backoff via injected sleeper, 4 additional tests covering 200/503/retry-then-success/give-up-after-second-failure.
- **GitHub:** https://github.com/samrathsingh302/comp3011-search-engine (public, branch `main`)
- **CI status:** last run green on Python 3.10, 3.11, 3.12 ([run 26051783956](https://github.com/samrathsingh302/comp3011-search-engine/actions/runs/26051783956))
- **Outstanding minor items:** `actions/checkout@v4` and `actions/setup-python@v5` emit Node-20 deprecation warnings on CI. Non-blocking; bump to v5/v6 in a future `ci:` commit before submission.
