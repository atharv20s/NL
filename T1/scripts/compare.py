"""
compare.py — Historical comparison: find the previous analytics run.

Scans ~/analytics-reports/ for valid dated folders, picks the most recent
one before the current run date, loads its raw CSVs, and returns them.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from validate import validate_files
from parse import ParsedReports, parse_reports

log = logging.getLogger(__name__)

DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@dataclass
class PreviousRun:
    date_str: str          # "YYYY-MM-DD"
    raw_dir: Path
    csv_paths: list[str]
    parsed: ParsedReports


def _is_valid_dated_dir(path: Path) -> bool:
    """True if path is a directory with a valid YYYY-MM-DD name and a raw/ subdir with CSVs."""
    if not path.is_dir():
        return False
    if not DATE_PATTERN.match(path.name):
        return False
    raw = path / "raw"
    if not raw.is_dir():
        return False
    csvs = list(raw.glob("*.csv"))
    return len(csvs) > 0


def _parse_date(name: str) -> Optional[date]:
    try:
        return datetime.strptime(name, "%Y-%m-%d").date()
    except ValueError:
        return None


def find_previous_run(
    data_root: Path,
    current_date: date,
) -> Optional[PreviousRun]:
    """
    Find the most recent valid analytics run before current_date.

    Does NOT assume the previous run is exactly 7 days ago — scans all
    dated directories and picks the most recent valid one.

    Args:
        data_root:    Root analytics directory (e.g. C:/Users/.../analytics-reports/)
        current_date: The date of the current run.

    Returns:
        PreviousRun if found, None if this is the first run.
    """
    if not data_root.exists():
        log.info("No previous runs — data_root does not exist yet: %s", data_root)
        return None

    candidates: list[tuple[date, Path]] = []
    for child in data_root.iterdir():
        if not _is_valid_dated_dir(child):
            continue
        d = _parse_date(child.name)
        if d is None:
            continue
        if d < current_date:
            candidates.append((d, child))

    if not candidates:
        log.info("No previous analytics runs found before %s in %s", current_date, data_root)
        return None

    candidates.sort(key=lambda x: x[0], reverse=True)
    prev_date, prev_dir = candidates[0]
    raw_dir = prev_dir / "raw"

    csv_paths = [str(p) for p in raw_dir.glob("*.csv")]
    log.info(
        "Previous run found: %s (%s) — %d CSV(s)",
        prev_date, prev_dir.name, len(csv_paths),
    )

    # Validate and parse the previous week's CSVs
    validation = validate_files(csv_paths)
    if not validation.validated:
        log.warning(
            "Previous run at %s found but no CSVs could be validated: %s",
            prev_dir.name,
            [str(e) for e in validation.errors],
        )
        return None

    parsed = parse_reports(validation.validated)

    return PreviousRun(
        date_str=prev_date.isoformat(),
        raw_dir=raw_dir,
        csv_paths=csv_paths,
        parsed=parsed,
    )
