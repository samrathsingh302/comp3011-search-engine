"""Storage: atomic JSON persistence for the inverted index."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_INDEX_PATH = Path("data/index.json")


class IndexNotFoundError(FileNotFoundError):
    """Raised when `load_index` cannot find a saved index at the requested path.

    Subclasses `FileNotFoundError` so callers that catch the broader exception
    still work. The more specific class lets the CLI render a friendly
    "no index loaded; try `build` first" message without having to inspect
    errno or message strings.
    """


def save_index(
    index_data: dict[str, Any], path: str | Path = DEFAULT_INDEX_PATH
) -> Path:
    """Write `index_data` to `path` atomically and return the resolved path.

    The write is two-phase: data is serialised to a temp file in the same
    directory as `path`, then `os.replace` swaps it into place. A crash
    mid-write therefore leaves either the previous file untouched or no
    file at all, never a half-written file that a later `load_index` would
    fail to parse.

    When `index_data["metadata"]` is a dict, a `saved_at` ISO-8601 UTC
    timestamp is added to it (overwriting any prior value). The temp file
    is cleaned up if any step before the `os.replace` raises.
    """
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)

    metadata = index_data.get("metadata")
    if isinstance(metadata, dict):
        metadata["saved_at"] = datetime.now(timezone.utc).isoformat()

    fd, tmp_path = tempfile.mkstemp(
        prefix=target.name + ".",
        suffix=".tmp",
        dir=str(target.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(index_data, handle, indent=2, ensure_ascii=False)
        os.replace(tmp_path, target)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:  # pragma: no cover - tmpfile guaranteed to exist at this point
            pass
        raise

    return target


def load_index(path: str | Path = DEFAULT_INDEX_PATH) -> dict[str, Any]:
    """Read and parse the JSON index at `path`.

    Raises `IndexNotFoundError` (a `FileNotFoundError` subclass) with a
    friendly message when no file exists at the requested path so the CLI
    can suggest running `build` instead of leaking a stack trace.
    """
    target = Path(path)
    if not target.exists():
        raise IndexNotFoundError(
            f"No index found at {target}. Run `build` from the CLI to create one."
        )
    with target.open("r", encoding="utf-8") as handle:
        data: dict[str, Any] = json.load(handle)
    return data


def index_exists(path: str | Path = DEFAULT_INDEX_PATH) -> bool:
    """Return True iff a file exists at `path`."""
    return Path(path).exists()
