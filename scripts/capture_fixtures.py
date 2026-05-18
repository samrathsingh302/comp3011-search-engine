"""Capture HTML fixtures from quotes.toscrape.com for the test suite.

Run this script ONCE. It fetches the first three pages with a real 6-second
politeness window and saves them under `tests/fixtures/`. Tests then load
the saved HTML instead of hitting the live network, which keeps them fast
and deterministic.

Usage (from the repo root):
    .\\.venv\\Scripts\\python.exe scripts\\capture_fixtures.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import requests


URLS: list[str] = [
    "https://quotes.toscrape.com/",
    "https://quotes.toscrape.com/page/2/",
    "https://quotes.toscrape.com/page/3/",
]

USER_AGENT = "COMP3011-CW2-Crawler/1.0 (educational; respects robots.txt)"
POLITENESS_SECONDS = 6.0
TIMEOUT_SECONDS = 10.0

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "tests" / "fixtures"


def main() -> int:
    """Fetch the URLs in order, with the politeness window between requests."""
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    for index, url in enumerate(URLS, start=1):
        if index > 1:
            print(f"... sleeping {POLITENESS_SECONDS} s before next fetch")
            time.sleep(POLITENESS_SECONDS)

        try:
            response = session.get(url, timeout=TIMEOUT_SECONDS)
        except requests.RequestException as exc:
            print(f"FAILED to reach {url}: {exc}")
            return 1

        if response.status_code != 200:
            print(f"FAILED status {response.status_code} for {url}")
            return 1

        out_path = FIXTURES_DIR / f"page{index}.html"
        out_path.write_text(response.text, encoding="utf-8")
        print(f"saved {out_path.name} ({len(response.text)} bytes from {url})")

    print("done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
