"""Print metadata for the saved index."""

from __future__ import annotations

import json
from pathlib import Path

with open(Path("data") / "index.json", encoding="utf-8") as f:
    d = json.load(f)
meta = d["metadata"]
print(f"pages={meta['document_count']}, terms={meta['term_count']}, version={meta['version']}")
print(f"options={meta.get('options', {})}")
