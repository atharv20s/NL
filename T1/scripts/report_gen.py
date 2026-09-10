"""
report_gen.py — HTML report generation via Jinja2.

Receives an AnalyticsResult and Interpretation, renders the Jinja2 template,
and returns the HTML string. No file I/O here — that's persist.py's job.
"""

from __future__ import annotations

import logging
import math
from datetime import datetime, date
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

from analytics import AnalyticsResult, KPIMetric
from interpret import Interpretation

log = logging.getLogger(__name__)

TEMPLATE_DIR = Path(__file__).parent.parent / "templates"
TEMPLATE_FILE = "report.html.j2"


def _fmt_duration(seconds: float) -> str:
    s = int(round(abs(seconds)))
    return f"{s // 60}:{s % 60:02d}"


def generate_report(
    result: AnalyticsResult,
    interpretation: Interpretation,
    week_date: str,
    data_root: str,
    site_name: str = "My Site",
) -> str:
    """
    Render the Jinja2 template with structured data from AnalyticsResult
    and Interpretation.

    Args:
        result:         Fully-calculated AnalyticsResult.
        interpretation: Interpretation object with narrative text.
        week_date:      ISO date string for this reporting week.
        data_root:      Path to the analytics-reports root directory.
        site_name:      Display name for the site.

    Returns:
        HTML string (self-contained, ready to write to disk).
    """
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(["html"]),
    )

    # Register helper filter
    env.filters["abs"] = abs
    env.globals["format_duration"] = _fmt_duration

    # ── Build template context ────────────────────────────────────────────
    now = datetime.now()

    # Traffic KPIs
    traffic_kpis = [
        result.sessions,
        result.users,
        result.new_users,
        result.avg_session_duration,
        result.bounce_rate,
    ]

    # Search KPIs
    search_kpis = [
        result.total_clicks,
        result.total_impressions,
        result.site_ctr,
        result.avg_position,
    ] if result.total_clicks.value > 0 else []

    # Channel chart arrays
    channel_labels = [ch.channel for ch in result.channels]
    channel_tw     = [round(ch.sessions_tw, 1) for ch in result.channels]
    channel_lw     = [round(ch.sessions_lw, 1) for ch in result.channels]

    # Device donut data (show as % of total, rounded to 1dp)
    total_dev_sessions = sum(d.sessions for d in result.devices) or 1
    device_labels = [d.device_category for d in result.devices]
    device_data   = [round(d.sessions / total_dev_sessions * 100, 1) for d in result.devices]

    # Date range display
    date_range = f"Week of {week_date}"
    if result.comparison_week_date:
        date_range += f"  ·  vs. {result.comparison_week_date}"

    # Parse bold markers in narrative (** → <strong>)
    def _bold(text: str) -> str:
        import re
        return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)

    summary_paragraphs = [_bold(p) for p in interpretation.summary_paragraphs]

    context = dict(
        # Meta
        site_name=site_name,
        week_date=week_date,
        date_range=date_range,
        generated_at=now.strftime("%Y-%m-%d %H:%M"),
        data_root=data_root,
        has_prior_data=result.has_prior_data,
        comparison_date=result.comparison_week_date,

        # Narrative
        summary_paragraphs=summary_paragraphs,
        key_findings=interpretation.key_findings,
        anomalies=interpretation.anomalies,
        action_item=_bold(interpretation.action_item),

        # Traffic
        traffic_kpis=traffic_kpis,
        sessions_day_labels=result.sessions_day_labels,
        sessions_by_day_tw=result.sessions_by_day_tw,
        sessions_by_day_lw=result.sessions_by_day_lw if result.has_prior_data else [],

        # Channels
        channels=result.channels,
        channel_labels=channel_labels,
        channel_tw_data=channel_tw,
        channel_lw_data=channel_lw if result.has_prior_data else [],

        # Search
        search_kpis=search_kpis,
        top_queries=result.top_queries,
        growing_queries=result.growing_queries,

        # Landing pages
        top_landing_pages=result.top_landing_pages,
        biggest_gainers=result.biggest_gainers,
        biggest_droppers=result.biggest_droppers,

        # Device
        devices=result.devices,
        device_labels=device_labels,
        device_data=device_data,

        # Engagement
        site_avg_engagement_time=result.site_avg_engagement_time,
        top_engaged_pages=result.top_engaged_pages,
        engagement_improved=result.engagement_improved,
        engagement_declined=result.engagement_declined,
    )

    template = env.get_template(TEMPLATE_FILE)
    html = template.render(**context)
    log.info("Report generated (%d bytes)", len(html.encode("utf-8")))
    return html
