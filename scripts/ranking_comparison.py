"""Generate side-by-side TF-IDF vs BM25 top-3 results per query for the README."""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Make `src.*` importable when the script is invoked from the project root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.indexer import InvertedIndex  # noqa: E402
from src.search import SearchEngine  # noqa: E402

QUERIES = ["love", "life", "world", "good friends", "indifference"]

with open(Path("data") / "index.json", encoding="utf-8") as f:
    data = json.load(f)
idx = InvertedIndex.from_dict(data)

out_lines = ["| query | ranking | rank | score | url |", "|---|---|---|---|---|"]
for q in QUERIES:
    for r in ("tfidf", "bm25"):
        eng = SearchEngine(idx, ranking=r)
        hits = eng.find(q, limit=3)
        for i, h in enumerate(hits, 1):
            out_lines.append(f"| `{q}` | {r} | {i} | {h.score:.3f} | {h.url} |")

table = "\n".join(out_lines)
print(table)
Path("docs/ranking_comparison.txt").write_text(table, encoding="utf-8")
