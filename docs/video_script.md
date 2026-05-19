# COMP3011 CW2 Video Script (4:30 target, 4:50 ceiling)

Read aloud at a normal pace. Bracketed lines are stage directions, not spoken. Replace `<your name>` with your actual name on the day. If you run over 4:40, trim from the **code walkthrough** commentary first (keep the file open + the one-sentence label per file); never trim the live demo commands.

Estimated word count: ~402 spoken words, ~3 minutes 20 seconds of narration. The remaining ~70 seconds is the live-demo action: command typing, watching output, the one polite pause during `build`. Target total: 4:30.

---

## 0:00 - 0:15 Intro

> Hello, I'm `<your name>`. This is my COMP3011 Coursework 2 submission: a command-line search engine that crawls `quotes.toscrape.com`, builds an inverted index with positional information, and answers queries with TF-IDF or BM25 ranking.

[Show: terminal with the project directory visible.]

---

## 0:15 - 2:15 Live demo (2 minutes; brief's allocation)

[Run: `python -m src.main`. The COMP3011 banner appears.]

> First, **build**. Crawls with 6-second politeness, parses robots.txt, builds the inverted index. I'll let it complete one polite pause, then Ctrl-C; the real index is already on disk.

[Type: `build`. Wait until you hear/see one ~6-second pause between fetches, then Ctrl-C.]

> **Load** reads the pre-built index from disk. 214 pages, 4,729 terms.

[Type: `load`. Read the confirmation line.]

> **Print** returns the inverted-index entry for a single word. `print indifference` — eleven documents contain it. Each posting shows frequency, the `in_title` flag, and positions.

[Type: `print indifference`. Pause briefly so the viewer can read the first posting.]

> **Find** returns ranked pages containing all query terms. `find good friends` — top result is the friends-tag page with a TF-IDF score of 24.89.

[Type: `find good friends`. Pause on the top result.]

> **Find** also handles typos. `find indiffirence` — no pages contain that, but the engine offers `indifference` via Python's `difflib` at a 0.7 similarity cutoff.

[Type: `find indiffirence`. Point to the "did you mean" line.]

> **Stats** gives corpus statistics. 214 pages, 4,729 terms, top word is "the" at 1,275 occurrences.

[Type: `stats`. Pause on the top-10 list.]

> **Exit.**

[Type: `exit`.]

---

## 2:15 - 3:30 Code walkthrough (1:15)

[Open `src/indexer.py` in the editor. Scroll to the `TITLE_BODY_POSITION_GAP` constant near the top.]

> Open `src/indexer.py`. `TITLE_BODY_POSITION_GAP = 1000`. Field-weighted indexing from Lecture 12. Title tokens occupy positions zero through N; body tokens start at 1000. Phrase proximity cannot match across the title-body boundary by construction.

[Open `src/search.py`. Scroll to the BM25 constants and `_bm25_score` method.]

> Open `src/search.py`. `BM25_K1 = 1.5`, `BM25_B = 0.75`. Okapi BM25 from Robertson and Walker, 1994, with the +0.5 IDF smoothing the paper actually publishes. The `--ranking` flag on `find` lets me compare TF-IDF and BM25 on the same query mid-session; the README has a full side-by-side comparison.

[Open `src/crawler.py`. Scroll to the `crawl` method's main loop.]

> Open `src/crawler.py`. The BFS loop from Lecture 9. `_effective_delay` between requests respects both my 6-second floor and any `Crawl-delay` declared in `robots.txt`. The sleeper is injected at constructor time, so unit tests mock it; every crawler test runs in milliseconds.

---

## 3:30 - 4:00 Tests, lint, version control (0:30 combined)

[Run: `pytest --cov=src`. Let the green bar render.]

> Run pytest. 127 tests pass. Coverage 100 percent, with 11 defensive lines pragma'd with one-line justifications.

[Run: `ruff check src/ tests/` then `mypy src/`.]

> Ruff clean. Mypy clean.

[Run: `git log --oneline --decorate -10`.]

> 27 commits across two days, five semantic tags from `v0.2-crawler` through `v0.9-tests-passing`.

[Switch to browser: open the GitHub Actions tab on the repo.]

> GitHub Actions: green on Python 3.10, 3.11, and 3.12.

---

## 4:00 - 4:30 GenAI evaluation (0:30; the 15% mark)

[Open `GENAI_EVALUATION.md`. Scroll to Section 3.]

> Two concrete moments from `GENAI_EVALUATION.md` Section 3. First: the AI typed `cmd.Cmd.emptyline` as returning `None`. Mypy flagged it against the typeshed stub, which declares `bool`. I changed it to return `False`. Second: the AI wrote `python -c` with PowerShell variable interpolation, which strips embedded double quotes — Python crashed with `SyntaxError: parenthesis never closed`. I switched the launcher to pipe via stdin to `python -`. Twelve more events are logged verbatim in `GENAI_EVALUATION.md` Section 3 and `docs/decisions.md`.

---

## 4:30 End

[Stop recording.]
