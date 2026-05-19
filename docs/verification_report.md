# COMP3011 CW2 Submission Verification Report

## Automated estimate: 93.5 / 100

**Caveats — read these before reacting to the number:**

- This is an AUTOMATED estimate. Marker score may differ by +/- 10 points.
- Video quality (audio, pacing, clarity) is not auto-checkable; a placeholder 3.0/4.5 is awarded.
- GenAI evaluation authenticity is not checked — only length and structure. A marker reading Section 3 looks at whether your AI-correction quotes match real events.
- Subjective aspects (design rationale quality, narrative coherence in the README, lecture connection depth) are not auto-assessed.
- This script cannot guarantee any specific grade.

## ✓ Crawling Implementation — 8.5/10 (85%)

- ✓ Crawler class defined (1.5/1.5)
- ✓ CrawlerConfig defined (1.0/1.0)
- ✗ 6s+ politeness delay (0.0/1.5)
- ✓ Uses BeautifulSoup (1.0/1.0)
- ✓ Uses requests (0.5/0.5)
- ✓ robots.txt handling (1.5/1.5)
- ✓ BFS / queue traversal (1.5/1.5)
- ✓ Error handling (try/except) (1.0/1.0)
- ✓ Timeout configured (0.5/0.5)

## ✓ Indexing Implementation — 10.0/10 (100%)

- ✓ InvertedIndex class (2.0/2.0)
- ✓ tokenize function (1.0/1.0)
- ✓ Stores frequency (1.0/1.0)
- ✓ Stores positions (1.5/1.5)
- ✓ in_title field weighting (1.0/1.0)
- ✓ Title/body position gap (0.5/0.5)
- ✓ body_excerpt stored (1.0/1.0)
- ✓ Stopword support (0.5/0.5)
- ✓ Stemming support (0.5/0.5)
- ✓ to_dict / from_dict (1.0/1.0)

## ✓ Storage & Retrieval — 8.0/8 (100%)

- ✓ save_index function (1.5/1.5)
- ✓ load_index function (1.5/1.5)
- ✓ IndexNotFoundError defined (1.0/1.0)
- ✓ Atomic writes (tempfile + os.replace) (2.0/2.0)
- ✓ Timestamps recorded (0.5/0.5)
- ✓ data/index.json valid (214 pages, 4729 terms) (1.5/1.5)

## ✓ Search Functionality — 12.0/12 (100%)

- ✓ CLI: do_build (1.0/1.0)
- ✓ CLI: do_load (1.0/1.0)
- ✓ CLI: do_print (1.0/1.0)
- ✓ CLI: do_find (1.0/1.0)
- ✓ SearchEngine class (1.0/1.0)
- ✓ AND intersection / shortest-list-first (1.5/1.5)
- ✓ TF-IDF ranking (1.5/1.5)
- ✓ BM25 ranking (1.5/1.5) — extension beyond brief
- ✓ Snippet generation (1.0/1.0)
- ✓ Typo suggestions (1.0/1.0)
- ✓ --ranking flag in CLI (0.5/0.5) — extension beyond brief

## ✓ Testing & Coverage — 20.0/20 (100%)

- ✓ pytest passes (127 tests) (8.0/8.0)
- ✓ Coverage: 100.0% (8.0/8.0) — target: 90%+ for 80-100 band
- ✓ ruff clean (2.0/2.0)
- ✓ mypy clean (2.0/2.0)

## ✓ Code Quality & Documentation — 11.0/10 (110%)

- ✓ Module docstrings (6/6) (2.0/2.0)
- ✓ Type hints on return (54/54 functions) (2.0/2.0)
- ✓ README has project overview/purpose (0.5/0.5)
- ✓ README has setup/install (0.5/0.5)
- ✓ README has usage with all 4 commands (0.5/0.5)
- ✓ README has testing instructions (0.5/0.5)
- ✓ README has architecture / design decisions (0.5/0.5)
- ✓ README has references / lectures cited (0.5/0.5)
- ✓ README has limitations / future work (0.5/0.5)
- ✓ requirements.txt (1.0/1.0)
- ✓ pyproject.toml (ruff config) (1.0/1.0)
- ✓ Dependencies pinned (3/3) (1.5/1.5) — exact pins (==) needed for reproducible CI

## ✓ Version Control — 5.0/5 (100%)

- ✓ Commit count (29) (2.0/2.0) — target: 24+ for organic dev
- ✓ Conventional Commits (29/29 = 100%) (2.0/2.0)
- ✓ Milestone tags (6) (1.0/1.0) — v0.2-crawler, v0.3-indexer-storage, v0.4-search, v0.5-cli, v0.9-tests-passing, v1.0-submission

## ✓ Video Demonstration — 8.0/10 (80%)

- ✓ video_script.md exists (1.0/1.0)
- ✓ Script ends at ~290s (target <=290s) (1.0/1.0) — brief penalises 5:00+
- ✓ Script: Live demo section (0.5/0.5)
- ✓ Script: Code walkthrough (0.5/0.5)
- ✓ Script: Testing section (0.5/0.5)
- ✓ Script: Version control / git (0.5/0.5)
- ✓ Script: GenAI section (0.5/0.5)
- ✓ scripts/demo_runner.py for recording aid (0.5/0.5)
- ✓ MANUAL: video recorded, <=4:50, uploaded as YouTube Unlisted (3.0/4.5) — AUTO-AWARDED PLACEHOLDER; verify manually before submission

## ~ GenAI Critical Evaluation — 11.0/15 (73%)

- ✓ Tools Used (1.0/1.0)
- ✓ Where AI Helped (1.0/1.0)
- ✓ AI Mistakes / Corrections (1.0/1.0)
- ✓ Quality discussion (1.0/1.0)
- ✓ Learning impact (1.0/1.0)
- ✓ Time management (1.0/1.0)
- ✓ Ethical considerations (1.0/1.0)
- ✓ Failure log / appendix (1.0/1.0)
- ✗ AI-note entries in decisions.md (0) (0.0/2.0) — target: 5+ genuine entries to draw on
- ✗ AI-note references in evaluation (0) (0.0/2.0) — target: 3+ verbatim quotes in Section 3
- ✓ Evaluation length (46479 chars) (3.0/3.0) — target: 2500+ chars for substantive evaluation

## Top issues by point value

- **2.0 pts** at stake — GenAI Critical Evaluation: AI-note references in evaluation (0) (target: 3+ verbatim quotes in Section 3)
- **2.0 pts** at stake — GenAI Critical Evaluation: AI-note entries in decisions.md (0) (target: 5+ genuine entries to draw on)
- **1.5 pts** at stake — Video Demonstration: MANUAL: video recorded, <=4:50, uploaded as YouTube Unlisted (AUTO-AWARDED PLACEHOLDER; verify manually before submission)
- **1.5 pts** at stake — Crawling Implementation: 6s+ politeness delay

## Manual review required

Run these checks yourself before submitting:
- [ ] Watch your video end-to-end; confirm length is <= 4:50; audio is clear; text on screen is legible
- [ ] Open GENAI_EVALUATION.md Section 3; open docs/decisions.md; confirm every cited AI mistake quote appears verbatim in decisions.md
- [ ] Read README.md design decisions section; are the choices project-specific or could they apply to any project?
- [ ] Sample 5 source functions; do their docstrings describe intent, not just restate the name?
- [ ] Verify GitHub Actions is green for the latest commit on all configured Python versions
- [ ] Confirm YouTube video is Unlisted (not Private, not Public)
- [ ] Test the YouTube URL in an Incognito browser window
- [ ] Confirm Minerva submission contains: video URL, GitHub URL, statement about data/index.json location

## How to interpret the score

Map to brief grading bands (rough guide; markers exercise judgment):
- 80-100: outstanding to exceptional; novel contributions; publication-quality code
- 70-79: very good; optimised algorithms; professional Git; insightful GenAI eval
- 60-69: good; robust implementation; consistent workflow; thoughtful GenAI eval
- 50-59: satisfactory; commands work; reasonable coverage; adequate explanations
- 40-49: pass; basic implementation; some testing; superficial GenAI eval

An automated estimate of 85 does not guarantee an 85 from the marker. The most likely range is +/- 10.
