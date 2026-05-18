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
