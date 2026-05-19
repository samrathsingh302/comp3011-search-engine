"""Teleprompter for the COMP3011 CW2 recording.

Run on a second monitor (or in a side terminal) during the live demo. Press
Enter to reveal each command in turn; the presenter then types the command
into a separate `(search)` shell window. The teleprompter does not drive the
search shell directly — that would make the recording feel mechanical.

Usage:
    python scripts/demo_runner.py
"""

from __future__ import annotations

DEMO_LINES: list[tuple[str, str]] = [
    ("python -m src.main", "launch the search shell"),
    ("build", "crawl with 6s politeness; let one pause complete; Ctrl-C"),
    ("load", "reload the saved index from disk"),
    ("print indifference", "read one posting aloud; show frequency / in_title / positions"),
    ("find good friends", "read the top result and its TF-IDF score"),
    ("find indiffirence", "read the 'did you mean: indifference' suggestion"),
    ("stats", "read pages, terms, and the top-1 word"),
    ("exit", "close the shell, end of live demo"),
]


def main() -> None:
    print("COMP3011 CW2 demo teleprompter.")
    print("Press Enter to reveal each command; type it manually in the (search) window.")
    print()
    for index, (command, note) in enumerate(DEMO_LINES, start=1):
        input(f"[{index}/{len(DEMO_LINES)}] Press Enter to reveal the next command...")
        print()
        print(f"  >>> {command}")
        print(f"  ({note})")
        print()
    print("End of demo. Stop recording.")


if __name__ == "__main__":
    main()
