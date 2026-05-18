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
