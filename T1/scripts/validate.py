"""
validate.py — CSV identification and validation layer.

Identifies which of the 6 GA4 report types each CSV file represents,
then validates required columns are present and the file is non-empty.

All logic here is deterministic; no LLM involved.
"""

from __future__ import annotations

import csv
import io
import logging
import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

# ── Report type enum ──────────────────────────────────────────────────────────

class ReportType(str, Enum):
    TRAFFIC_OVERVIEW  = "traffic_overview"
    CHANNEL_GROUPING  = "channel_grouping"
    LANDING_PAGES     = "landing_pages"
    SEARCH_QUERIES    = "search_queries"
    DEVICE_BREAKDOWN  = "device_breakdown"
    PAGE_ENGAGEMENT   = "page_engagement"
    UNKNOWN           = "unknown"


# ── Column signatures ─────────────────────────────────────────────────────────
# Each entry: (required_columns, discriminating_columns, filename_keywords)
# Matching is case-insensitive. We use a scoring approach so partial matches
# still succeed even if GA4 renames a column slightly.

# Hard-override discriminators: if ANY of these column substrings appear,
# the report type is determined immediately without scoring.
# Keys are column substrings; values are the resulting ReportType.
# Ordered from most specific to least specific.
HARD_OVERRIDES: list[tuple[str, ReportType]] = [
    ("device category",               ReportType.DEVICE_BREAKDOWN),
    ("session default channel group",  ReportType.CHANNEL_GROUPING),
    ("landing page",                   ReportType.LANDING_PAGES),
    ("average engagement time",        ReportType.PAGE_ENGAGEMENT),
    ("average position",               ReportType.SEARCH_QUERIES),
]

REPORT_SIGNATURES: list[tuple[ReportType, list[str], list[str], list[str]]] = [
    (
        ReportType.SEARCH_QUERIES,
        # required
        ["query", "clicks", "impressions"],
        # discriminating (at least 1 must be present)
        ["query", "impressions", "ctr", "average position"],
        # filename keywords
        ["query", "search", "search_console", "searchconsole"],
    ),
    (
        ReportType.CHANNEL_GROUPING,
        ["session default channel group", "sessions"],
        ["session default channel group", "channel group", "channel"],
        ["channel", "acquisition", "traffic_acquisition"],
    ),
    (
        ReportType.LANDING_PAGES,
        ["landing page", "sessions"],
        ["landing page", "landing_page"],
        ["landing", "landing_page"],
    ),
    (
        ReportType.DEVICE_BREAKDOWN,
        ["device category", "sessions"],
        ["device category", "device_category"],
        ["device", "device_breakdown", "tech"],
    ),
    (
        ReportType.PAGE_ENGAGEMENT,
        ["average engagement time", "views"],
        ["average engagement time", "engagement time"],
        ["engagement", "page_engagement", "pages_and_screens"],
    ),
    (
        ReportType.TRAFFIC_OVERVIEW,
        ["sessions"],
        ["sessions", "active users", "new users", "bounce rate"],
        ["traffic_overview", "overview", "sessions"],
    ),
]

REQUIRED_COLUMNS: dict[ReportType, list[str]] = {
    ReportType.TRAFFIC_OVERVIEW:  ["sessions"],
    ReportType.CHANNEL_GROUPING:  ["session default channel group", "sessions"],
    ReportType.LANDING_PAGES:     ["landing page", "sessions"],
    ReportType.SEARCH_QUERIES:    ["query", "clicks", "impressions"],
    ReportType.DEVICE_BREAKDOWN:  ["device category", "sessions"],
    ReportType.PAGE_ENGAGEMENT:   ["average engagement time"],
}


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class ValidationError:
    path: str
    message: str

    def __str__(self) -> str:
        return f"[{Path(self.path).name}] {self.message}"


@dataclass
class ValidatedReport:
    report_type: ReportType
    path: str
    original_filename: str
    header_row_index: int          # 0-based index of the actual header row
    columns: list[str]             # normalised column names
    row_count: int                 # data rows (excluding header)
    warnings: list[str] = field(default_factory=list)


@dataclass
class ValidationResult:
    validated: list[ValidatedReport] = field(default_factory=list)
    errors: list[ValidationError]   = field(default_factory=list)

    @property
    def success(self) -> bool:
        return len(self.errors) == 0

    @property
    def report_types_found(self) -> set[ReportType]:
        return {r.report_type for r in self.validated}

    def missing_report_types(self) -> list[ReportType]:
        standard = {rt for rt in ReportType if rt != ReportType.UNKNOWN}
        return sorted(standard - self.report_types_found, key=lambda x: x.value)

    def get(self, report_type: ReportType) -> Optional[ValidatedReport]:
        for r in self.validated:
            if r.report_type == report_type:
                return r
        return None


# ── Internal helpers ──────────────────────────────────────────────────────────

def _normalise(s: str) -> str:
    """Lowercase, strip whitespace."""
    return s.strip().lower()


def _find_header_row(rows: list[list[str]], max_search: int = 10) -> Optional[int]:
    """
    GA4 CSV exports prepend 2-6 metadata rows before the real header.
    Detect the header row by finding the first row that contains known
    GA4 metric/dimension column name fragments.
    """
    HEADER_SIGNALS = {
        "sessions", "users", "query", "clicks", "impressions", "views",
        "device", "channel", "page", "date", "bounce", "engagement",
        "landing", "position", "ctr", "new users", "active users",
    }
    for i, row in enumerate(rows[:max_search]):
        normalised = [_normalise(c) for c in row]
        if sum(1 for c in normalised if any(sig in c for sig in HEADER_SIGNALS)) >= 2:
            return i
    return None


def _score_type(
    normalised_cols: list[str],
    filename: str,
    signature: tuple[ReportType, list[str], list[str], list[str]],
) -> int:
    """
    Score a CSV against a report type signature.
    Higher = better match.
    """
    rtype, required, discriminating, filename_kws = signature
    score = 0
    fname_lower = filename.lower()

    # Filename keyword match (bonus)
    for kw in filename_kws:
        if kw in fname_lower:
            score += 3
            break

    # Discriminating column match
    for disc in discriminating:
        if any(disc in col for col in normalised_cols):
            score += 2

    # Required column match
    for req in required:
        if any(req in col for col in normalised_cols):
            score += 1

    return score


# ── Public API ────────────────────────────────────────────────────────────────

def identify_report_type(path: str, filename: str) -> tuple[ReportType, int, list[str], int]:
    """
    Read the CSV, find the header row, identify the report type.

    Returns: (report_type, header_row_index, normalised_columns, data_row_count)
    Raises: ValueError only if the file is empty.
    Returns UNKNOWN (not raises) if no GA4 column names are found.
    """
    with open(path, "r", encoding="utf-8-sig", newline="") as fh:
        content = fh.read()

    reader = csv.reader(io.StringIO(content))
    rows = list(reader)

    if not rows:
        raise ValueError("File is empty")

    header_idx = _find_header_row(rows)
    if header_idx is None:
        # No recognisable GA4 columns — return UNKNOWN with row 0 as header
        raw_columns = rows[0] if rows else []
        normalised_cols = [_normalise(c) for c in raw_columns if c.strip()]
        data_rows = [r for r in rows[1:] if any(c.strip() for c in r)]
        log.debug(
            "identify_report_type: %s → UNKNOWN (no GA4 header found, cols=%s)",
            filename, normalised_cols[:5],
        )
        return ReportType.UNKNOWN, 0, normalised_cols, len(data_rows)

    raw_columns = rows[header_idx]
    normalised_cols = [_normalise(c) for c in raw_columns if c.strip()]
    data_rows = [r for r in rows[header_idx + 1:] if any(c.strip() for c in r)]

    # ── Hard-override: certain columns uniquely identify a report type ────
    for fragment, forced_type in HARD_OVERRIDES:
        if any(fragment in col for col in normalised_cols):
            log.debug(
                "identify_report_type: %s → %s (hard-override on '%s')",
                filename, forced_type.value, fragment,
            )
            return forced_type, header_idx, normalised_cols, len(data_rows)

    # ── Fallback: score every signature ───────────────────────────────────
    scores = [
        (_score_type(normalised_cols, filename, sig), sig[0])
        for sig in REPORT_SIGNATURES
    ]
    scores.sort(key=lambda x: x[0], reverse=True)

    best_score, best_type = scores[0]
    if best_score < 2:
        best_type = ReportType.UNKNOWN

    log.debug(
        "identify_report_type: %s → %s (score=%d, cols=%s)",
        filename, best_type.value, best_score, normalised_cols[:5],
    )

    return best_type, header_idx, normalised_cols, len(data_rows)


def validate_files(file_paths: list[str]) -> ValidationResult:
    """
    Validate a list of CSV file paths.
    Each file is identified, type-checked, and required columns are verified.

    Args:
        file_paths: Absolute paths to CSV files.

    Returns:
        ValidationResult with validated reports and any errors.
    """
    result = ValidationResult()
    type_seen: dict[ReportType, str] = {}   # prevent duplicates

    for path in file_paths:
        filename = os.path.basename(path)
        log.info("Validating: %s", filename)

        # ── Basic file checks ─────────────────────────────────────────────
        if not os.path.exists(path):
            result.errors.append(ValidationError(path, "File does not exist"))
            continue

        if os.path.getsize(path) == 0:
            result.errors.append(ValidationError(path, "File is empty (0 bytes)"))
            continue

        # ── Identify & parse ──────────────────────────────────────────────
        try:
            rtype, header_idx, columns, row_count = identify_report_type(path, filename)
        except Exception as exc:
            result.errors.append(ValidationError(path, f"Could not parse CSV: {exc}"))
            continue

        warnings: list[str] = []

        if rtype == ReportType.UNKNOWN:
            result.errors.append(
                ValidationError(path, "Could not identify report type from columns/filename")
            )
            continue

        # ── Check required columns ────────────────────────────────────────
        required = REQUIRED_COLUMNS.get(rtype, [])
        missing_cols = []
        for req in required:
            if not any(req in col for col in columns):
                missing_cols.append(req)
        if missing_cols:
            result.errors.append(
                ValidationError(
                    path,
                    f"Report type {rtype.value} is missing required columns: {missing_cols}",
                )
            )
            continue

        # ── Warn on empty data ────────────────────────────────────────────
        if row_count == 0:
            warnings.append("File contains no data rows (header only)")

        # ── Warn on duplicate report types ────────────────────────────────
        if rtype in type_seen:
            warnings.append(
                f"Duplicate report type {rtype.value} — "
                f"already seen in {type_seen[rtype]}. This file will be ignored."
            )
            log.warning("Duplicate report type %s: %s vs %s", rtype.value, path, type_seen[rtype])
            # Don't error — just warn and skip
            continue

        type_seen[rtype] = path

        vr = ValidatedReport(
            report_type=rtype,
            path=path,
            original_filename=filename,
            header_row_index=header_idx,
            columns=columns,
            row_count=row_count,
            warnings=warnings,
        )
        result.validated.append(vr)

        for w in warnings:
            log.warning("[%s] %s", filename, w)
        log.info(
            "  ✓ %s → %s (%d data rows, %d columns)",
            filename, rtype.value, row_count, len(columns),
        )

    return result
