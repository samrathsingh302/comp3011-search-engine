# Final Verification Report

## Automated score

**93.5 / 100** from `scripts/verify_submission.py` (run from `comp3011-verifier/verify_submission.py` with the project venv on PATH so `pytest`, `ruff`, and `mypy` resolve correctly).

A first run *without* the venv on PATH produced 74.5/100 because the verifier invokes those three tools as bare commands (`subprocess.run(["pytest", ...])`) which then fall back to system PATH where the project's tools are not installed. The 93.5 number is the correct automated read.

### Verifier false negatives identified

Three regex bugs in `verify_submission.py` cost ~5.5 extra points that have nothing to do with the project:

| Bug | What the script looks for | What the project actually has | Pts lost |
|---|---|---|---|
| Politeness regex | `delay_seconds\s*[:=]\s*(?:6\.0\|...)` | `delay_seconds: float = 6.0` (annotated dataclass field, type sits between name and value) | 1.5 |
| AI note count in decisions.md | unformatted `AI note:` | `**AI note**:` (bold markdown) → 13 blocks present, 0 detected | 2.0 |
| AI note references in evaluation | same regex | 26 `**AI note**` strings present in `GENAI_EVALUATION.md`, 0 detected | 2.0 |

**Corrected automated estimate (accounting for verifier bugs only, no qualitative adjustment yet): 99.0 / 100** with the video item still placeholdered at 3.0/4.5 pending the user's recording and upload.

## Qualitative adjustments

### (A) README quality — no adjustment

Seven sections rated 0-3:

| Section | Score | Notes |
|---|---|---|
| Project overview | 2 | Specific: 214 pages / 4,729 terms / 4.2 MB / learning outcomes named |
| Architecture diagram | 2 | Mermaid graph plus per-component prose |
| Design decisions | 2 | Four prose paragraphs each grounded in a specific design choice |
| Complexity analysis | 2 | Table + paragraph noting "politeness dominates build" and slowest query 2.6 ms |
| Benchmark results | 3 | Verbatim table from `scale_benchmark.txt` + honest "what these numbers do and do not show" |
| Ranking comparison | 3 | Verbatim table from `ranking_comparison.txt` + concrete observation (BM25 surfaces Mark Twain quote at #1, TF-IDF picks high-TF friends-tag page) |
| Lecture references | 2 | Paragraph per L9 / L11 / L12 / L13 naming specific implementation hooks |

Average **2.3 / 3**. No section scoring 0 or 1; no "must fix" flags.

### (B) GenAI authenticity audit — no adjustment

- Total AI-mistake blocks in `GENAI_EVALUATION.md` Section 3: **12 blocks containing 14 sub-bullet events** (two blocks have two sub-bullets each).
- Blocks that match `docs/decisions.md` verbatim: **12 / 12** (each was copy-pasted from the corresponding `## ...` decision entry in decisions.md).
- Blocks that look paraphrased or invented: **0**.
- Risk flag: **none**. Fabrication would have been the highest-risk item; the audit clears it.

### (C) Commit message audit — no adjustment

- Total commits on `main`: **29**
- Conventional Commits format (`type(scope): description`): **29 / 29 = 100%**
- Messages describing only WHAT without WHY: ~0-2. Most messages name the feature added or the chore performed (e.g. `feat(search): add Okapi BM25 ranking (Robertson Walker 1994)` — names the algorithm and the citation). None are pure `update file` or `fix bug` style.
- Specific weak commits: none with obvious gaps.

### (D) Docstring quality sample — no adjustment

Five `def` lines sampled at random across `src/`:

| Function | File:line | Rating | Notes |
|---|---|---|---|
| `extract_visible_text` | indexer.py:118 | 2 | Explains *why* head is stripped (avoids title double-count) |
| `load_index` | storage.py:66 | 2 | Explains exception class rationale (CLI suggests `build`) |
| `_add_occurrence` | indexer.py:202 | 2 | One line but mentions the `in_title` promotion rule |
| `do_load` | cli.py:93 | 1 | One-liner ("load: Read a previously-saved inverted index from disk."). Intentionally short because it doubles as cmd.Cmd auto-help text |
| `_load_robots` | crawler.py:137 | 2 | Three explicit behaviour cases + the brief's 6-second floor as a lower bound |

Average **1.8 / 2**. Strong. The one rated 1 is intentional (auto-help target).

### (E) Lecture connection check — no adjustment

Lecture references found in `src/` via `git grep -i "lecture" src/`:

- **L9** in `crawler.py` (Web Crawling: BFS, politeness, robots.txt, graceful failure)
- **L11** in `indexer.py` (Parsing and Tokenisation: edge cases, regex design)
- **L12** in `search.py` and `indexer.py` (Indexing, extents, field weighting)
- **L13** in `search.py` (Query Processing: shortest-list-first conjunctive evaluation)

**All four required lectures cited in their correct modules**. No gaps.

## Final estimate range

- **Low**: 93 (strict marker, video has minor issues)
- **Mid**: 96 (verifier regex bugs corrected, video uploaded successfully)
- **High**: 99 (full credit on the video manual item)

**Most likely band**: **80-100 (outstanding to exceptional)** per the brief's grading band descriptions. The 80-100 band requires "novel contributions or particularly creative solutions"; the project's dual-ranker `--ranking` flag, the explicit BM25-vs-TF-IDF comparison table, the 100% coverage with auditable pragma justifications, and the 14-event GenAI evaluation grounded in real `decisions.md` entries all satisfy that requirement.

## Top 5 highest-leverage fixes

| Rank | Fix | Expected gain | Time | Priority |
|---|---|---|---|---|
| 1 | **Record + upload the video to YouTube Unlisted** | +1.5 pts (placeholder 3.0/4.5 → real 4.5/4.5) | ~1 hour | **DO** |
| 2 | **Submit on Minerva** with video URL + repo URL + index note | No points (it's the gate, not a scoring criterion) | 10 min | **DO** |
| 3 | Optionally expand `do_load` docstring beyond the cmd.Cmd help line (1 → 2 rating) | Marginal | 2 min | SKIP |
| 4 | Fix `verify_submission.py` politeness regex to recognise annotated dataclass fields | None (the project already meets the criterion; this just makes the verifier honest) | 5 min | SKIP — verifier bug, not ours |
| 5 | Fix `verify_submission.py` AI-note regex to match `**AI note**:` | None (same reason) | 5 min | SKIP — verifier bug, not ours |

## Submit or not?

**Submit now.**

Reasoning:
- Code at 100% test coverage on 127 tests, ruff clean, mypy clean, CI green on Python 3.10/3.11/3.12.
- README is 212 lines with every output block traceable to a real captured source.
- GenAI evaluation is 14 verbatim AI-correction events, all backed by `decisions.md` entries written at the moment they occurred.
- 29 commits in Conventional Commits format with six semantic tags from `v0.2-crawler` through `v1.0-submission`.
- The remaining `+5.5` points the verifier under-reports are all script bugs in regex patterns, not real gaps in the project.

The only fix that adds real points from here is the video recording. Once that MP4 exists and is uploaded as Unlisted with a working incognito URL, do the Minerva submission and the project is done.

---

*Generated 2026-05-19 from `comp3011-verifier/verify_submission.py` (automated) + the qualitative review pass per `comp3011-verifier/verify-prompt.txt`. No source files were modified by this report; only `docs/verification_report.md` (created by the script) and this `docs/final_verification.md` (created by the review) are new on disk.*
