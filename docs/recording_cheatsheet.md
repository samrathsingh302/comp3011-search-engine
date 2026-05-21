# Recording cheatsheet (dress rehearsal verified 2026-05-21)

Read this once before recording. Every number and word in here has been confirmed against the live code and the committed `data/index.json`.

## Demo words confirmed in the index

| Word | Pages | Use for |
|---|---|---|
| `nonsense` | 6 | `print` (brief example, **works**) |
| `indifference` | 11 | `find` single-word (brief example, **works**) |
| `good` + `friends` | 38 + 169 | `find good friends` multi-word (**works**) |
| `love` / `life` | 167 / 189 | backup single-word queries (very common) |
| `indiffirence` (typo) | 0, but **triggers did-you-mean** | use for the suggestion edge case |
| `xyznotaword` | 0, **no suggestions** | use only if you want plain "no pages" |

**Important substitution**: the kit's shotlist suggests `find xyznotaword` for the non-existent-word edge case, but that returns only `No pages contain all of: xyznotaword` with **no did-you-mean line** (difflib's 0.7 cutoff finds nothing close to random gibberish). To demonstrate the suggestion feature the voiceover describes, use **`find indiffirence`** instead — that returns `No pages contain all of: indiffirence` plus `indiffirence: did you mean indifference, difference?` Use one or the other (or both); my recommendation is `find indiffirence` because it shows more behaviour.

## Command sequence in order (use this, on camera)

```
chcp 65001              # ensures Unicode smart-quotes in snippets render correctly
python -m src.main
build                   # wait for ONE polite pause, ~6s, then Ctrl+C
python -m src.main      # relaunch (Ctrl+C exits the shell entirely — see note below)
load
print nonsense
find indifference
find good friends
find indiffirence       # the brief's non-existent-word edge case (with suggestions)
find                    # the brief's empty-query edge case
stats
exit
```

Then (in the same or a fresh PowerShell):

```
pytest --cov=src
ruff check src/ tests/
mypy src/
git log --oneline --decorate -12
git tag -l
```

Then alt-tab to the browser on the GitHub Actions tab.

## Behaviour you'll see on camera (verified from a real dry run)

- `load` → `Loaded 214 pages (4729 terms) from data\index.json.`
- `print nonsense` → 6 documents, each with `frequency=1, in_title=False, positions=[...]`
- `find indifference` → `Found 11 matching page(s) for: indifference`, `Ranking: TFIDF`. Top result: `https://quotes.toscrape.com/tag/indifference/page/1/`, score `23.3144`.
- `find good friends` → `Found 20 matching page(s)`. Top: `tag/friends/`, score `24.8869`.
- `find indiffirence` → `No pages contain all of: indiffirence` + `indiffirence: did you mean indifference, difference?`
- `find` (empty) → `Usage: find [--ranking tfidf|bm25] <query>` (does NOT crash; clean usage line)
- `stats` → `Pages: 214 / Terms: 4729 / Total postings: 21946 / Top 10 terms by total frequency: the (1275), to (1045), by (949), and (764), of (762), a (758), in (659), quotes (642), tags (575), about (457)`
- `exit` → `Goodbye.`

## Critical behaviour: Ctrl+C during `build`

When you press Ctrl+C during `build`, **the entire shell exits** with the message `Goodbye (interrupted).` (no traceback, no red error). It does NOT return you to the `(search)` prompt. **You must relaunch `python -m src.main` to continue.**

The kit's shotlist anticipates this option ("If Ctrl+C drops you out of the shell entirely, just relaunch with `python -m src.main`"). Just do that on camera.

## Code walkthrough — exact line numbers

| File | Constant / method | Line |
|---|---|---|
| `src/indexer.py` | `TITLE_BODY_POSITION_GAP = 1000` | **20** |
| `src/search.py` | `TITLE_BOOST = 2.0` | **16** |
| `src/search.py` | `def _bm25_score(...)` | **143** |
| `src/crawler.py` | `delay_seconds: float = 6.0  # Brief mandates >= 6 seconds...` | **46** |
| `src/crawler.py` | `def _load_robots(self) -> None:` | **137** |
| `src/crawler.py` | `self.sleeper(self._effective_delay)` (the actual sleep call) | **240** |

In VS Code: `Ctrl+G`, type the line number, Enter. Scroll a couple of lines up so the surrounding context is visible on camera.

## Real numbers for the voiceover brackets

| Bracket | Value to say |
|---|---|
| `[CONFIRMED WORD]` for `print` | `nonsense` |
| `[CONFIRMED SINGLE WORD]` for single-word `find` | `indifference` |
| `[INSERT REAL NUMBER]` tests | **127** |
| `[INSERT REAL PERCENT]` coverage | **100** (state it as "one hundred percent" or "100 percent" — strictly that's the line coverage with 11 defensive lines `# pragma: no cover`'d; mention that if you want extra credibility) |
| `[INSERT REAL COMMIT COUNT]` commits | **30** |
| `[YOUR AI TOOL]` | `Claude Code` (or `Claude Code with the Opus 4.7 model` if you want to be precise) |
| `[YOUR NAME]` | Samrath Singh (or whatever you actually want on YouTube) |

## Two real GenAI mistakes (verbatim from `GENAI_EVALUATION.md` Section 3)

Both dated **2026-05-19**. Each is one of the 14 logged events. Word them naturally in the voiceover but the underlying facts must match these:

**Mistake 1 — mypy override mismatch (`cmd.Cmd over argparse` section)**:

> First-pass `emptyline()` was typed `-> None`. Mypy flagged `error: Return type "None" of "emptyline" incompatible with return type "bool" in supertype "cmd.Cmd" [override]` — the typeshed stub for `cmd.Cmd.emptyline` declares `-> bool` (returning truthy ends the loop). Changed to `-> bool` and `return False`.

**Suggested voiceover phrasing (~16 words)**: "The AI typed `cmd.Cmd.emptyline` as returning None. Mypy flagged it against the typeshed stub, which declared bool. I changed it to return False."

**Mistake 2 — PowerShell argv quoting (`Staging the real crawl during dev` section)**:

> First-pass `run_real_crawl.ps1` used `python -c "$pythonCode"`. PowerShell's Win32-argv encoding does not escape embedded `"` characters when interpolating a variable into a native command line, so the double-quoted strings in the Python source arrived at `python.exe` unquoted. Python crashed at parse time on `print(Starting real crawl...)` — `SyntaxError: '(' was never closed`. Switched the script to pipe the source via stdin to `python -`.

**Suggested voiceover phrasing (~18 words)**: "The AI wrote `python dash-c` with PowerShell variable interpolation, which strips embedded double quotes. Python crashed with `SyntaxError, parenthesis never closed`. I switched the launcher to pipe via stdin to `python dash`."

## Tests / lint / CI numbers for screen reference

- `pytest --cov=src` → **127 passed**, **100% coverage** (TOTAL 569 stmts, 0 missing)
- `ruff check src/ tests/` → `All checks passed!`
- `mypy src/` → `Success: no issues found in 7 source files`
- CI: green on Python 3.10/3.11/3.12 — latest run at https://github.com/samrathsingh302/comp3011-search-engine/actions

## Tags to point at during the version-control section

```
v0.2-crawler
v0.3-indexer-storage
v0.4-search
v0.5-cli
v0.9-tests-passing
v1.0-submission
```

Six semantic tags across 30 commits. Conventional Commit prefixes (`feat:`, `test:`, `docs:`, `chore:`, `ci:`, `data:`) visible in `git log --oneline --decorate -12`.

## Quirks / gotchas to be aware of mid-take

1. **Smart-quote rendering**: snippets contain U+201C / U+201D curly quotes. PowerShell's default code page (CP 437) renders them as `?` or `�`. Run `chcp 65001` once at the start of the recording session to force UTF-8 console output. The smart quotes then appear correctly on camera.
2. **Ctrl+C from `build`** exits the shell with `Goodbye (interrupted).` — relaunch with `python -m src.main` before `load`. **No red traceback** appears, which is what the brief checks for.
3. **Empty `find`** prints `Usage: find [--ranking tfidf|bm25] <query>` and returns to the `(search)` prompt cleanly. No crash.
4. **`find xyznotaword`** prints only `No pages contain all of: xyznotaword` (no suggestion line). Use `find indiffirence` instead to get the did-you-mean behaviour the voiceover describes.
5. **`build` takes minutes if you let it run.** The brief's 6-second politeness means a full crawl is ~22 minutes. The shotlist plan is to let one polite pause complete (~7-8 seconds of visible "Crawling ..." then a pause), then Ctrl+C and switch to `load`. You never let `build` finish on camera.

## Pre-record checklist (final, before pressing record)

- [ ] PowerShell font ≥ 24 (right-click title bar → Properties → Font)
- [ ] Run `chcp 65001` once in the PowerShell window
- [ ] `cls` to clear the screen
- [ ] Type `cd C:\Users\samra\comp3011-cw2` if not already there
- [ ] Confirm venv active (prompt shows `(.venv)`) or run `.\.venv\Scripts\Activate.ps1`
- [ ] VS Code open with three tabs: `src/indexer.py`, `src/search.py`, `src/crawler.py`
- [ ] Browser tab on https://github.com/samrathsingh302/comp3011-search-engine/actions
- [ ] OBS / Game Bar set up at 720p+, 30 FPS, mic OFF (silent pass)
- [ ] Focus Assist ON or notifications muted
- [ ] This cheatsheet open on a SECOND screen (not the captured one), or printed

When you're confident, hit record and follow `video-recording-kit/silent-recording-shotlist.md` step by step using the words and line numbers above.

---

*Generated from a dress rehearsal on 2026-05-21. Source: actual outputs of `python -m src.main` piped through the same command sequence the shotlist uses, plus `git`, `pytest`, `ruff`, `mypy` runs from the project root. All values verified against the committed code and `data/index.json`.*
