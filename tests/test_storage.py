"""Tests for src.storage."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from src.storage import (
    IndexNotFoundError,
    index_exists,
    load_index,
    save_index,
)


def _sample_data() -> dict[str, Any]:
    """Return a minimal but structurally complete index payload."""
    return {
        "metadata": {"version": "1.0", "term_count": 1, "document_count": 1},
        "documents": {"http://example.com/": {"title": "hi", "word_count": 1}},
        "index": {
            "hi": {
                "http://example.com/": {
                    "frequency": 1,
                    "positions": [0],
                    "in_title": True,
                }
            }
        },
    }


class TestSaveIndex:
    def test_save_index_creates_file(self, tmp_path: Path) -> None:
        target = tmp_path / "index.json"
        save_index(_sample_data(), target)
        assert target.exists()

    def test_save_index_writes_valid_json(self, tmp_path: Path) -> None:
        target = tmp_path / "index.json"
        save_index(_sample_data(), target)
        loaded = json.loads(target.read_text(encoding="utf-8"))
        assert loaded["metadata"]["version"] == "1.0"
        assert loaded["index"]["hi"]["http://example.com/"]["frequency"] == 1

    def test_save_records_saved_at_timestamp(self, tmp_path: Path) -> None:
        target = tmp_path / "index.json"
        save_index(_sample_data(), target)
        loaded = json.loads(target.read_text(encoding="utf-8"))
        assert "saved_at" in loaded["metadata"]
        # ISO-8601 UTC timestamp ends with +00:00 or Z
        assert loaded["metadata"]["saved_at"].endswith("+00:00")

    def test_save_index_creates_parent_directories(self, tmp_path: Path) -> None:
        target = tmp_path / "nested" / "deeper" / "index.json"
        save_index(_sample_data(), target)
        assert target.exists()
        assert target.parent.is_dir()


class TestLoadIndex:
    def test_load_index_round_trip(self, tmp_path: Path) -> None:
        target = tmp_path / "index.json"
        original = _sample_data()
        save_index(original, target)
        loaded = load_index(target)
        assert loaded["index"] == original["index"]
        assert loaded["documents"] == original["documents"]

    def test_load_index_raises_friendly_error_when_missing(self, tmp_path: Path) -> None:
        target = tmp_path / "does-not-exist.json"
        with pytest.raises(IndexNotFoundError) as excinfo:
            load_index(target)
        assert "No index found" in str(excinfo.value)
        # IndexNotFoundError is a FileNotFoundError, so broader handlers still catch it.
        assert isinstance(excinfo.value, FileNotFoundError)


class TestIndexExists:
    def test_index_exists_returns_false_for_missing(self, tmp_path: Path) -> None:
        assert index_exists(tmp_path / "no.json") is False

    def test_index_exists_returns_true_after_save(self, tmp_path: Path) -> None:
        target = tmp_path / "index.json"
        save_index(_sample_data(), target)
        assert index_exists(target) is True


class TestAtomicWrite:
    def test_atomic_write_leaves_no_tmp_file(self, tmp_path: Path) -> None:
        """A successful save must leave no `.tmp` siblings behind."""
        target = tmp_path / "index.json"
        save_index(_sample_data(), target)
        assert list(tmp_path.glob("*.tmp")) == []

    def test_save_cleans_up_tmp_when_json_dump_fails(self, tmp_path: Path) -> None:
        """A failure during json.dump must remove the temp file and re-raise."""
        target = tmp_path / "index.json"
        with patch("src.storage.json.dump", side_effect=RuntimeError("boom")):
            with pytest.raises(RuntimeError, match="boom"):
                save_index(_sample_data(), target)
        # Temp file must NOT remain, and the target must NOT have been created.
        assert list(tmp_path.glob("*.tmp")) == []
        assert not target.exists()
