"""
persist.py — File persistence layer (idempotent).

Creates the dated folder structure, copies raw CSVs, writes the HTML report,
and saves run-metadata.json. Safe to run multiple times for the same date.
"""

from __future__ import annotations

import json
import logging
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)


@dataclass
class RunMetadata:
    run_date: str
    generated_at: str
    comparison_date: Optional[str]
    mode: str                  # "live" | "dry-run"
    input_files: list[str]
    report_types_found: list[str]
    row_counts: dict[str, int]
    report_path: str
    warnings: list[str]


def setup_run_directory(data_root: Path, run_date: str) -> tuple[Path, Path]:
    """
    Create (or reuse) the dated directory structure:
        data_root/
        └── YYYY-MM-DD/
            ├── raw/
            └── report/

    Returns: (raw_dir, report_dir)
    """
    run_dir    = data_root / run_date
    raw_dir    = run_dir / "raw"
    report_dir = run_dir / "report"

    raw_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)

    log.info("Run directory: %s", run_dir)
    return raw_dir, report_dir


def save_raw_csvs(source_paths: list[str], raw_dir: Path) -> list[str]:
    """
    Copy source CSV files to raw_dir.
    Preserves original filenames. Existing files are overwritten (idempotent).

    Returns: list of destination paths.
    """
    saved: list[str] = []
    for src in source_paths:
        src_path = Path(src)
        dest = raw_dir / src_path.name
        shutil.copy2(str(src_path), str(dest))
        log.info("  Saved raw: %s → %s", src_path.name, dest)
        saved.append(str(dest))
    return saved


def write_report(html: str, report_dir: Path, run_date: str) -> Path:
    """
    Write the HTML report to report_dir/weekly-report-YYYY-MM-DD.html.
    Overwrites if already exists (idempotent).

    Returns: Path to the written file.
    """
    filename = f"weekly-report-{run_date}.html"
    out_path = report_dir / filename
    out_path.write_text(html, encoding="utf-8")
    log.info("  Report written: %s (%d bytes)", out_path, len(html.encode("utf-8")))
    return out_path


def write_metadata(
    metadata: RunMetadata,
    run_dir: Path,
) -> Path:
    """
    Write run-metadata.json to run_dir.
    Overwrites if already exists (idempotent).

    Returns: Path to the written file.
    """
    meta_path = run_dir / "run-metadata.json"
    with open(meta_path, "w", encoding="utf-8") as fh:
        json.dump(asdict(metadata), fh, indent=2)
    log.info("  Metadata written: %s", meta_path)
    return meta_path
