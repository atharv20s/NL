"""
parse.py — Deterministic CSV parsing layer.

Reads validated CSV files into typed Python dataclasses.
No arithmetic happens here — only type conversion and normalisation.
"""

from __future__ import annotations

import csv
import io
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import pandas as pd

from validate import ReportType, ValidatedReport

log = logging.getLogger(__name__)

# ── Column name aliases ───────────────────────────────────────────────────────
# Maps possible GA4 column names → our canonical internal name.
# Keys are lowercase substrings to match against.

COLUMN_ALIASES: dict[str, str] = {
    # Traffic Overview / shared
    "date":                          "date",
    "sessions":                      "sessions",
    "active users":                  "active_users",
    "new users":                     "new_users",
    "bounce rate":                   "bounce_rate",
    "engagement rate":               "engagement_rate",
    "average session duration":      "avg_session_duration",
    "user engagement duration":      "avg_engagement_time",

    # Channel Grouping
    "session default channel group": "channel",

    # Landing Pages
    "landing page":                  "page",

    # Search Queries
    "query":                         "query",
    "clicks":                        "clicks",
    "impressions":                   "impressions",
    "ctr":                           "ctr",
    "average position":              "avg_position",

    # Device Breakdown
    "device category":               "device_category",

    # Page Engagement
    "page path":                     "page",
    "average engagement time":       "avg_engagement_time",
    "views":                         "views",
}


# ── Parsed data classes ───────────────────────────────────────────────────────

@dataclass
class TrafficOverviewRow:
    date: Optional[str]
    sessions: float
    active_users: float
    new_users: float
    bounce_rate: float      # 0–1
    engagement_rate: float  # 0–1
    avg_session_duration: float  # seconds


@dataclass
class ChannelRow:
    channel: str
    sessions: float
    new_users: float
    bounce_rate: float
    engagement_rate: float


@dataclass
class LandingPageRow:
    page: str
    sessions: float
    new_users: float
    bounce_rate: float
    avg_session_duration: float


@dataclass
class SearchQueryRow:
    query: str
    clicks: float
    impressions: float
    ctr: float        # 0–1
    avg_position: float


@dataclass
class DeviceRow:
    device_category: str
    sessions: float
    new_users: float
    bounce_rate: float


@dataclass
class PageEngagementRow:
    page: str
    avg_engagement_time: float  # seconds
    views: float
    engagement_rate: float


@dataclass
class ParsedReports:
    traffic_overview:  list[TrafficOverviewRow]  = field(default_factory=list)
    channel_grouping:  list[ChannelRow]          = field(default_factory=list)
    landing_pages:     list[LandingPageRow]      = field(default_factory=list)
    search_queries:    list[SearchQueryRow]      = field(default_factory=list)
    device_breakdown:  list[DeviceRow]           = field(default_factory=list)
    page_engagement:   list[PageEngagementRow]   = field(default_factory=list)
    parse_warnings:    list[str]                 = field(default_factory=list)


# ── Numeric helpers ───────────────────────────────────────────────────────────

def _to_float(value: str, col: str, row_idx: int) -> float:
    """Convert a GA4 string value to float, handling commas, %, empty."""
    if not isinstance(value, str):
        try:
            return float(value)
        except (ValueError, TypeError):
            return 0.0

    v = value.strip().replace(",", "").replace("\xa0", "")
    if not v or v in ("-", "N/A", "n/a", "(not set)"):
        return 0.0

    is_pct = v.endswith("%")
    if is_pct:
        v = v[:-1]

    try:
        f = float(v)
    except ValueError:
        log.debug("_to_float: cannot parse '%s' in col=%s row=%d", value, col, row_idx)
        return 0.0

    # Normalise percentages to 0–1
    # Heuristic: if the column is a rate/ctr and the value is > 1, divide by 100
    if is_pct:
        f = f / 100.0
    elif col in ("bounce_rate", "engagement_rate", "ctr") and f > 1.0:
        f = f / 100.0

    return f


# ── Core dataframe loader ─────────────────────────────────────────────────────

def _load_dataframe(vr: ValidatedReport) -> pd.DataFrame:
    """
    Load a validated CSV into a pandas DataFrame, skipping metadata rows,
    using the detected header row, and canonicalising column names.
    """
    with open(vr.path, "r", encoding="utf-8-sig", newline="") as fh:
        content = fh.read()

    rows = list(csv.reader(io.StringIO(content)))
    if vr.header_row_index >= len(rows):
        return pd.DataFrame()

    header = rows[vr.header_row_index]
    data_rows = rows[vr.header_row_index + 1:]

    # Drop fully-empty rows
    data_rows = [r for r in data_rows if any(c.strip() for c in r)]

    # Pad short rows
    n = len(header)
    data_rows = [r + [""] * max(0, n - len(r)) for r in data_rows]
    # Truncate long rows
    data_rows = [r[:n] for r in data_rows]

    df = pd.DataFrame(data_rows, columns=header)

    # Canonicalise column names
    rename_map: dict[str, str] = {}
    for raw_col in df.columns:
        normalised = raw_col.strip().lower()
        for fragment, canonical in COLUMN_ALIASES.items():
            if fragment in normalised:
                rename_map[raw_col] = canonical
                break
    df.rename(columns=rename_map, inplace=True)

    # Drop rows where the first column is empty (GA4 sometimes adds empty trailing rows)
    first_col = df.columns[0]
    df = df[df[first_col].str.strip() != ""]

    return df


def _safe_col(df: pd.DataFrame, col: str) -> pd.Series:
    """Return column if present, else a zero series."""
    if col in df.columns:
        return df[col]
    return pd.Series(["0"] * len(df))


# ── Per-report parsers ────────────────────────────────────────────────────────

def _parse_traffic_overview(vr: ValidatedReport) -> list[TrafficOverviewRow]:
    df = _load_dataframe(vr)
    rows = []
    for i, row in df.iterrows():
        rows.append(TrafficOverviewRow(
            date=str(row.get("date", "")).strip() or None,
            sessions=_to_float(str(_safe_col(df, "sessions")[i]), "sessions", i),
            active_users=_to_float(str(_safe_col(df, "active_users")[i]), "active_users", i),
            new_users=_to_float(str(_safe_col(df, "new_users")[i]), "new_users", i),
            bounce_rate=_to_float(str(_safe_col(df, "bounce_rate")[i]), "bounce_rate", i),
            engagement_rate=_to_float(str(_safe_col(df, "engagement_rate")[i]), "engagement_rate", i),
            avg_session_duration=_to_float(str(_safe_col(df, "avg_session_duration")[i]), "avg_session_duration", i),
        ))
    return rows


def _parse_channel_grouping(vr: ValidatedReport) -> list[ChannelRow]:
    df = _load_dataframe(vr)
    rows = []
    for i, row in df.iterrows():
        channel = str(_safe_col(df, "channel")[i]).strip()
        if not channel or channel.lower() in ("", "(not set)"):
            channel = "Unassigned"
        rows.append(ChannelRow(
            channel=channel,
            sessions=_to_float(str(_safe_col(df, "sessions")[i]), "sessions", i),
            new_users=_to_float(str(_safe_col(df, "new_users")[i]), "new_users", i),
            bounce_rate=_to_float(str(_safe_col(df, "bounce_rate")[i]), "bounce_rate", i),
            engagement_rate=_to_float(str(_safe_col(df, "engagement_rate")[i]), "engagement_rate", i),
        ))
    return rows


def _parse_landing_pages(vr: ValidatedReport) -> list[LandingPageRow]:
    df = _load_dataframe(vr)
    rows = []
    for i, row in df.iterrows():
        page = str(_safe_col(df, "page")[i]).strip() or "/"
        rows.append(LandingPageRow(
            page=page,
            sessions=_to_float(str(_safe_col(df, "sessions")[i]), "sessions", i),
            new_users=_to_float(str(_safe_col(df, "new_users")[i]), "new_users", i),
            bounce_rate=_to_float(str(_safe_col(df, "bounce_rate")[i]), "bounce_rate", i),
            avg_session_duration=_to_float(str(_safe_col(df, "avg_session_duration")[i]), "avg_session_duration", i),
        ))
    return rows


def _parse_search_queries(vr: ValidatedReport) -> list[SearchQueryRow]:
    df = _load_dataframe(vr)
    rows = []
    for i, row in df.iterrows():
        query = str(_safe_col(df, "query")[i]).strip()
        if not query or query.lower() == "(other)":
            continue
        rows.append(SearchQueryRow(
            query=query,
            clicks=_to_float(str(_safe_col(df, "clicks")[i]), "clicks", i),
            impressions=_to_float(str(_safe_col(df, "impressions")[i]), "impressions", i),
            ctr=_to_float(str(_safe_col(df, "ctr")[i]), "ctr", i),
            avg_position=_to_float(str(_safe_col(df, "avg_position")[i]), "avg_position", i),
        ))
    return rows


def _parse_device_breakdown(vr: ValidatedReport) -> list[DeviceRow]:
    df = _load_dataframe(vr)
    rows = []
    for i, row in df.iterrows():
        device = str(_safe_col(df, "device_category")[i]).strip().title()
        if not device:
            device = "Unknown"
        rows.append(DeviceRow(
            device_category=device,
            sessions=_to_float(str(_safe_col(df, "sessions")[i]), "sessions", i),
            new_users=_to_float(str(_safe_col(df, "new_users")[i]), "new_users", i),
            bounce_rate=_to_float(str(_safe_col(df, "bounce_rate")[i]), "bounce_rate", i),
        ))
    return rows


def _parse_page_engagement(vr: ValidatedReport) -> list[PageEngagementRow]:
    df = _load_dataframe(vr)
    rows = []
    for i, row in df.iterrows():
        page = str(_safe_col(df, "page")[i]).strip() or "/"
        rows.append(PageEngagementRow(
            page=page,
            avg_engagement_time=_to_float(str(_safe_col(df, "avg_engagement_time")[i]), "avg_engagement_time", i),
            views=_to_float(str(_safe_col(df, "views")[i]), "views", i),
            engagement_rate=_to_float(str(_safe_col(df, "engagement_rate")[i]), "engagement_rate", i),
        ))
    return rows


# ── Public API ────────────────────────────────────────────────────────────────

_PARSER_MAP = {
    ReportType.TRAFFIC_OVERVIEW: _parse_traffic_overview,
    ReportType.CHANNEL_GROUPING: _parse_channel_grouping,
    ReportType.LANDING_PAGES:    _parse_landing_pages,
    ReportType.SEARCH_QUERIES:   _parse_search_queries,
    ReportType.DEVICE_BREAKDOWN: _parse_device_breakdown,
    ReportType.PAGE_ENGAGEMENT:  _parse_page_engagement,
}


def parse_reports(validated_reports: list[ValidatedReport]) -> ParsedReports:
    """
    Parse a list of ValidatedReports into a ParsedReports dataclass.

    Args:
        validated_reports: Output from validate.validate_files().

    Returns:
        ParsedReports with populated fields for each report type found.
    """
    parsed = ParsedReports()

    for vr in validated_reports:
        parser = _PARSER_MAP.get(vr.report_type)
        if parser is None:
            parsed.parse_warnings.append(f"No parser for report type: {vr.report_type}")
            continue

        try:
            result = parser(vr)
            field_name = vr.report_type.value  # e.g. "traffic_overview"
            setattr(parsed, field_name, result)
            log.info(
                "  Parsed %s: %d rows from %s",
                vr.report_type.value, len(result), vr.original_filename,
            )
        except Exception as exc:
            msg = f"Parse error in {vr.original_filename}: {exc}"
            log.error(msg)
            parsed.parse_warnings.append(msg)

    return parsed
