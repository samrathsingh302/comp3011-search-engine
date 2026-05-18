# Design Decisions Log

A running log of design choices made during the build. Each entry captures the decision, the alternatives considered, and the rationale. Entries that involved an AI-suggested mistake are flagged with an **AI note** line so they can be quoted verbatim in `GENAI_EVALUATION.md`.

---

## 2026-05-18 — Storage format: JSON on disk

**Decision**: Persist the inverted index as a single JSON file at `data/index.json`.

**Alternatives considered**: `pickle` (faster to load, smaller on disk, but binary and version-fragile across Python releases); `sqlite3` (overkill for a single-file deliverable; introduces a schema-migration burden); a directory of per-term shards (premature optimisation at this corpus size).

**Rationale**: The coursework brief allows a single file. JSON is human-readable, which makes the file inspectable by the marker without running the project. The expected size is on the order of a few hundred kilobytes for around 100 pages — small enough that load time is irrelevant. The atomic-write step planned for `src/storage.py` will give the JSON file the same crash-safety that `pickle` would not have provided by default.

## 2026-05-18 — Smoke test in the initial scaffold

**Decision**: Include one trivial test in `tests/test_smoke.py` from the first commit, even though the plan suggested an empty test directory.

**Alternatives considered**: Run `pytest -q` with no tests at all.

**Rationale**: With no tests collected, `pytest` exits with status 5, which would trip the `commit_session.ps1` guard and block the first commit. A two-assertion smoke test (`1 + 1 == 2` plus `import src`) confirms both the test runner and the `src` package layout work, costs nothing, and lets the auto-commit helper succeed.

**AI note**: The original plan's instruction "Run `pytest -q` (it should pass trivially with no tests)" was based on an old assumption that pytest treats "no tests collected" as success. Modern pytest exits 5 in that case. Caught before running the helper for the first time; corrected by adding the smoke test.

## 2026-05-18 — CI: Python 3.10 / 3.11 / 3.12 matrix on ubuntu-latest with an 85% coverage gate

**Decision**: GitHub Actions runs the suite on three Python minor versions (3.10, 3.11, 3.12) with `fail-fast: false`, on `ubuntu-latest`, gated by `--cov-fail-under=85`.

**Alternatives considered**: a single-version job on the latest Python only (simpler, hides forward-compat issues); a wider matrix that also includes Windows and macOS runners (slower, costs minutes, gives little signal because the code has no platform-specific paths); a stricter `--cov-fail-under=90` gate (we'll get there, but the gate should not break the build on commits that are intentionally light on tests, e.g. pure-docs sessions).

**Rationale**: The coursework is graded on a marker's machine whose Python version we don't control. A three-version matrix proves the code runs unchanged on the entire currently-supported CPython range (3.13 came out as the latest stable; 3.10 is the oldest minor still in security maintenance at time of writing). `fail-fast: false` means all three jobs report even if one fails, which is what we want when diagnosing version-specific issues. The 85% floor is a baseline the build must always clear; the project target is 90% or higher and is asserted by individual test sessions, not by CI. Pip caching keyed on both requirements files keeps CI runs under a minute once warm.

**AI note**: First-draft workflow had `fail-fast` left at its default of `true`. Switched it off because hiding two of three matrix jobs on a single failure removes most of the diagnostic value of a matrix in the first place.

## 2026-05-18 — Fetch retry policy: once, on network-level errors only

**Decision**: `Crawler._fetch` retries exactly once with a 1-second backoff, and only on `requests.RequestException`. Non-200 HTTP statuses return `None` immediately with no retry.

**Alternatives considered**: retry on any failure including 4xx and 5xx (more aggressive, risks hammering a server that has already declined); exponential backoff with three retries (better for production crawlers, but a 6-second politeness floor already dominates the latency budget here, and three retries against a slow site can take a minute per page); no retry at all (drops legitimate transient failures, hurts crawl completeness).

**Rationale**: The distinction between "server answered, the answer is no" (non-200) and "couldn't even reach the server" (RequestException) is the right axis. We retry the second category once because the connection might genuinely be flaky. We refuse to retry the first because the server has expressed an opinion. The 1-second backoff is well under the 6-second politeness window, so retries do not blow the politeness budget when crawling. Lecture 9 explicitly calls out graceful failure handling as a crawler quality bar.

**AI note**: First-draft of `_fetch` looped over `(1, 2)` with `continue` and a trailing `return None`. The trailing return was unreachable, which both coverage and any half-decent linter flag. Restructured to a linear "try, except->sleep->retry, fall through to status check" so the dead code goes away. Cleaner and easier to read aloud during the video walkthrough.

## 2026-05-18 — BFS over DFS

**Decision**: `Crawler.crawl()` traverses with BFS using `collections.deque` as the queue and a local `visited: set[str]` scoped to the call.

**Alternatives considered**: DFS via recursion (simpler to write, but blows up on deep link chains, and on `quotes.toscrape.com` would dive into one author's quote pages before discovering the second pagination page); DFS via an explicit stack (same shape as BFS but worse traversal order for this site); a priority queue that prefers pagination links (premature optimisation when BFS already wins).

**Rationale**:
- **Discovery order.** BFS visits the seed, then every page reachable in one hop, then every page reachable in two hops, and so on. On `quotes.toscrape.com` that means we walk the pagination chain (`/`, `/page/2/`, `/page/3/`, ...) before drilling into author or tag pages. A `max_pages=N` cap therefore returns the most representative slice of the site, not whichever sub-tree we happened to descend first.
- **Visited set keyed on the normalised URL.** Using the output of `normalise_url` as the dedup key means `https://x.com/p`, `https://X.COM/p`, and `https://x.com/p#frag` all map to one fetch. Without normalisation we would crawl the same content three times and waste two units of the politeness budget.
- **Politeness applies BETWEEN requests only.** Sleeping before the first request would pointlessly delay every CLI `build` by 6 seconds for nothing. The flag `is_first_request` flips after the first iteration so all subsequent fetches pay the politeness toll.

**AI note**: Initial sketch put `visited` as an instance attribute (`self.visited`) so a second `crawl()` call on the same Crawler would carry old state. Decided that surprised the user (each `crawl()` should be a fresh traversal), so moved `visited` into the function body. The reference implementation keeps it on the instance; this is one deliberate divergence and is worth mentioning in the video.

## 2026-05-18 — robots.txt: graceful failure

**Decision**: `Crawler._load_robots()` is best-effort. A `RequestException` or any non-200 status leaves `_robot_parser` as `None`, which makes `_is_allowed` permissive for every URL. The crawl proceeds as if no policy were declared.

**Alternatives considered**: refuse to crawl when robots.txt is unreachable (safer for hostile sites but punishes the user for transient network blips on a well-behaved site like `quotes.toscrape.com`); cache the failure and retry mid-crawl (premature complexity for a one-domain, one-process crawler).

**Rationale**:
- **Missing robots is not the same as denial.** A 404 on `/robots.txt` is the canonical signal that the site has no policy; treating it as "deny everything" is a misread of RFC 9309.
- **Network blips are common.** A transient `ConnectionError` on `/robots.txt` followed by a crawl that proceeds at 6 second politeness is far less hostile than retrying forever.
- **Crawl-delay wins only if it is stricter.** `_effective_delay = max(config.delay_seconds, robots_crawl_delay)`. The brief's 6 second floor is a contractual minimum; we never drop below it just because a site asks us to. This protects the user's grade from any robots.txt that lies about being more permissive than the brief allows.

**Fixtures captured once via the live network.** `scripts/capture_fixtures.py` ran in the user's terminal with real `requests.Session` and a real 6 second sleep between fetches. The resulting `tests/fixtures/page{1,2,3}.html` files are committed so every subsequent test run uses identical HTML and never touches the live site again. This is the standard "record once, replay forever" pattern for crawler tests.

**AI note**: First-draft `_load_robots()` used `parser.set_url()` plus `parser.read()` (which performs its own HTTP call via urllib, bypassing the injected `requests.Session`). That broke the injection design and would have made the robots-related tests hit the network. Corrected by calling `parser.parse(response.text.splitlines())` instead, so all HTTP routes through `self.session` and stays mockable.

## 2026-05-18 — Linting and forward-compatible annotations

**Decision**: Add `ruff` (>= 0.4.0) to dev requirements and configure it in `pyproject.toml` with the rule set `[E, F, W, I, B, UP]`, line length 100, ignoring `E501`, and `B011` ignored for tests. The CI workflow runs `ruff check src/ tests/` after pytest. Every `src/` module starts with `from __future__ import annotations` (after the docstring).

**Alternatives considered**:
- `flake8` plus `isort` plus `pyupgrade` as separate tools (slow, three configs to maintain, no shared cache);
- `black` for formatting in addition to `ruff` (formatting drift is not a problem on a one-person, four-day project);
- `mypy` for static typing (valuable for the 80-100 band but it is a bigger investment than this bootstrap step warrants; revisit before submission).

**Rationale**:
- **Ruff covers PEP 8 (E, W), pyflakes-style bug finding (F), import ordering (I), bug-bear patterns (B), and pyupgrade modernisation (UP) in a single binary**, in roughly 200 ms on a project this size. The B and UP rule sets are the actual win: B caught `assert x or y` style traps in the past, UP catches deprecated typing patterns. The first run flagged `from typing import Callable` (UP035) and pushed it to `from collections.abc import Callable`, which is the Python 3.9+ idiom.
- **`from __future__ import annotations`** turns every annotation into a string at parse time (PEP 563). On Python 3.10 we get PEP 604 union syntax (`X | None`) and string-typed forward references for free, with zero runtime cost: the annotations are not evaluated unless something explicitly asks for them.  The `E501` ignore exists because line length is enforced by reading discipline, not by the linter shouting on every long-but-clear assertion.
- **CI step ordering**: pytest first, ruff second. If tests fail the build is already red and the lint output is noise; if tests pass we still demand a clean lint to merge.

**AI note**: Ruff's first complaint included `I001` in `tests/conftest.py` for an extra blank line between `import pytest` and the first module-level constant. Pre-ruff me had used the PEP 8 "two blank lines after imports" pattern; ruff's isort sub-tool prefers exactly one blank line in this context. Applied `ruff --fix` to take the suggestion rather than fight it; the resulting file is still PEP 8 valid because PEP 8 says "two or more" (allowing one in narrow cases).
