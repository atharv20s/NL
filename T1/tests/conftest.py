"""conftest.py — Shared pytest fixtures."""
import sys
from pathlib import Path

# Make scripts/ importable
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import pytest
import csv
import io
import os
import tempfile
from pathlib import Path


SAMPLE_CURRENT = Path(__file__).parent.parent / "sample_data" / "current_week"
SAMPLE_PREVIOUS = Path(__file__).parent.parent / "sample_data" / "previous_week"


def _write_csv(tmp_path: Path, filename: str, content: str) -> str:
    """Write CSV content to a temp file and return its path."""
    p = tmp_path / filename
    p.write_text(content, encoding="utf-8")
    return str(p)


@pytest.fixture
def tmp_csv(tmp_path):
    """Helper fixture: returns a function to write named CSVs to tmp_path."""
    def _make(filename: str, content: str) -> str:
        return _write_csv(tmp_path, filename, content)
    return _make


@pytest.fixture
def current_week_csvs():
    """Return all current week sample CSV paths."""
    return [str(p) for p in sorted(SAMPLE_CURRENT.glob("*.csv"))]


@pytest.fixture
def previous_week_csvs():
    """Return all previous week sample CSV paths."""
    return [str(p) for p in sorted(SAMPLE_PREVIOUS.glob("*.csv"))]
