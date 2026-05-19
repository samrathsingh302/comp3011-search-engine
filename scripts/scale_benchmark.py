"""Scale benchmark: median find() time per query across corpus subsets."""

from __future__ import annotations

import copy
import json
import statistics
import sys
import time
from pathlib import Path

# Make `src.*` importable when the script is invoked from the project root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.indexer import InvertedIndex  # noqa: E402
from src.search import SearchEngine  # noqa: E402

QUERIES = ["love", "life", "world", "good friends", "indifference"]

with open(Path("data") / "index.json", encoding="utf-8") as f:
    data = json.load(f)

# Soft consistency check — warn, don't refuse
if data["metadata"]["options"].get("remove_stopwords") is not False:
    print("WARNING: index was built with remove_stopwords=True; "
          "benchmark queries may behave differently than the README claims.")

all_docs = list(data["documents"].keys())
total = len(all_docs)
candidates = [5, 10, 25, 50]
subsets = sorted({min(n, total) for n in candidates if n < total} | {total})
print(f"Corpus size: {total}. Subset sizes: {subsets}")


def build_subset(size: int) -> InvertedIndex:
    subset_urls = set(all_docs[:size])
    sub = copy.deepcopy(data)
    sub["documents"] = {u: v for u, v in sub["documents"].items() if u in subset_urls}
    new_index: dict = {}
    for term, postings in sub["index"].items():
        filtered = {u: p for u, p in postings.items() if u in subset_urls}
        if filtered:
            new_index[term] = filtered
    sub["index"] = new_index
    sub["metadata"]["document_count"] = len(sub["documents"])
    sub["metadata"]["term_count"] = len(sub["index"])
    return InvertedIndex.from_dict(sub)


rows = []
for size in subsets:
    idx = build_subset(size)
    eng = SearchEngine(idx, ranking="tfidf")
    for q in QUERIES:
        timings = []
        for _ in range(10):
            t0 = time.perf_counter()
            eng.find(q)
            timings.append((time.perf_counter() - t0) * 1000)
        median_ms = statistics.median(timings)
        rows.append((size, q, median_ms))
        print(f"size={size:>3}  query={q!r:<22}  median_ms={median_ms:.3f}")

out = Path("docs") / "scale_benchmark.txt"
with open(out, "w", encoding="utf-8") as f:
    f.write("| subset_size | query | median_ms |\n")
    f.write("|---|---|---|\n")
    for size, q, ms in rows:
        f.write(f"| {size} | `{q}` | {ms:.3f} |\n")
print(f"\nSaved table to {out}")
