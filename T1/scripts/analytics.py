"""
analytics.py — Deterministic metric calculations.

All arithmetic, aggregations, percentages, and rankings happen here.
Zero LLM involvement. Every number in the final report is traceable to
this module.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

from parse import (
    ParsedReports, TrafficOverviewRow, ChannelRow,
    LandingPageRow, SearchQueryRow, DeviceRow, PageEngagementRow,
)

log = logging.getLogger(__name__)

# ── Utility ───────────────────────────────────────────────────────────────────

def _pct_change(current: float, previous: float) -> Optional[float]:
    """
    Returns ((current - previous) / |previous|) * 100 or None if previous == 0.
    Never divides by zero.
    """
    if previous == 0:
        return None
    return round(((current - previous) / abs(previous)) * 100, 1)


def _fmt_pct(val: Optional[float]) -> str:
    if val is None:
        return "N/A"
    sign = "+" if val >= 0 else ""
    return f"{sign}{val:.1f}%"


def _weighted_avg(values: list[float], weights: list[float]) -> float:
    """Weighted average. Returns 0.0 if total weight is 0."""
    total_w = sum(weights)
    if total_w == 0:
        return 0.0
    return sum(v * w for v, w in zip(values, weights)) / total_w


def _fmt_duration(seconds: float) -> str:
    """Format seconds as m:ss string."""
    s = int(round(seconds))
    return f"{s // 60}:{s % 60:02d}"


# ── Result dataclasses ────────────────────────────────────────────────────────

@dataclass
class KPIMetric:
    label: str
    value: float
    formatted: str     # ready-to-display string
    pct_change: Optional[float]   # None = no prior data
    change_formatted: str         # "+3.2%" / "-5.1%" / "N/A"
    direction: str                # "up" / "down" / "neutral"
    lower_is_better: bool = False


@dataclass
class ChannelMetric:
    channel: str
    sessions_tw: float
    sessions_lw: float
    change: float
    pct_change: Optional[float]


@dataclass
class LandingPageMetric:
    page: str
    sessions_tw: float
    sessions_lw: float
    new_users: float
    change: float
    pct_change: Optional[float]


@dataclass
class SearchQueryMetric:
    query: str
    clicks: float
    impressions: float
    ctr: float
    avg_position: float
    impression_pct_change: Optional[float]  # for "growing queries" detection


@dataclass
class DeviceMetric:
    device_category: str
    sessions: float
    share_pct: float          # this week
    share_pct_lw: float       # last week (0 if no prior data)
    share_shift: float        # this week minus last week


@dataclass
class PageEngagementMetric:
    page: str
    avg_engagement_time: float
    views: float
    engagement_time_change: Optional[float]  # pct change vs last week
    vs_site_avg: float   # seconds above/below site average


@dataclass
class AnalyticsResult:
    # ── Traffic Overview KPIs ─────────────────────────────────────────────
    sessions: KPIMetric
    users: KPIMetric
    new_users: KPIMetric
    avg_session_duration: KPIMetric
    bounce_rate: KPIMetric

    # Daily session series (for chart — may be empty if no date dimension)
    sessions_by_day_tw: list[float]
    sessions_by_day_lw: list[float]
    sessions_day_labels: list[str]

    # ── Channel ───────────────────────────────────────────────────────────
    channels: list[ChannelMetric]

    # ── Search ────────────────────────────────────────────────────────────
    total_clicks: KPIMetric
    total_impressions: KPIMetric
    avg_position: KPIMetric
    site_ctr: KPIMetric
    top_queries: list[SearchQueryMetric]   # top 20 by clicks
    growing_queries: list[SearchQueryMetric]  # impressions +10%+ WoW

    # ── Landing pages ─────────────────────────────────────────────────────
    top_landing_pages: list[LandingPageMetric]  # top 10 by sessions
    biggest_gainers: list[LandingPageMetric]    # top 3 by absolute gain
    biggest_droppers: list[LandingPageMetric]   # top 3 by absolute drop

    # ── Device ────────────────────────────────────────────────────────────
    devices: list[DeviceMetric]

    # ── Page engagement ───────────────────────────────────────────────────
    site_avg_engagement_time: float
    top_engaged_pages: list[PageEngagementMetric]   # top 10
    engagement_improved: list[PageEngagementMetric] # >= +20%
    engagement_declined: list[PageEngagementMetric] # <= -20%

    # ── Meta ──────────────────────────────────────────────────────────────
    has_prior_data: bool
    comparison_week_date: Optional[str]   # ISO date string or None


# ── Internal: aggregate parsed rows → scalar metrics ─────────────────────────

def _agg_traffic(rows: list[TrafficOverviewRow]) -> dict[str, float]:
    if not rows:
        return {"sessions": 0, "active_users": 0, "new_users": 0,
                "bounce_rate": 0, "engagement_rate": 0, "avg_session_duration": 0}
    total_sessions = sum(r.sessions for r in rows)
    total_users    = sum(r.active_users for r in rows)
    total_new      = sum(r.new_users for r in rows)
    # Weighted average for rate metrics
    weights = [r.sessions for r in rows]
    w_bounce = _weighted_avg([r.bounce_rate for r in rows], weights)
    w_engage = _weighted_avg([r.engagement_rate for r in rows], weights)
    w_dur    = _weighted_avg([r.avg_session_duration for r in rows], weights)
    return {
        "sessions":            total_sessions,
        "active_users":        total_users,
        "new_users":           total_new,
        "bounce_rate":         w_bounce,
        "engagement_rate":     w_engage,
        "avg_session_duration": w_dur,
    }


def _make_kpi(
    label: str,
    current: float,
    previous: Optional[float],
    fmt_fn=None,
    lower_is_better: bool = False,
) -> KPIMetric:
    pct = _pct_change(current, previous) if previous is not None else None
    if fmt_fn:
        formatted = fmt_fn(current)
    else:
        formatted = f"{int(current):,}" if current == int(current) else f"{current:,.1f}"

    direction = "neutral"
    if pct is not None:
        favourable = pct > 0
        if lower_is_better:
            favourable = pct < 0
        direction = "up" if favourable else "down"

    return KPIMetric(
        label=label,
        value=current,
        formatted=formatted,
        pct_change=pct,
        change_formatted=_fmt_pct(pct),
        direction=direction,
        lower_is_better=lower_is_better,
    )


# ── Public API ────────────────────────────────────────────────────────────────

def calculate(
    current: ParsedReports,
    previous: Optional[ParsedReports],
    comparison_date: Optional[str] = None,
) -> AnalyticsResult:
    """
    Calculate all metrics for the weekly report.

    Args:
        current:         ParsedReports for this week.
        previous:        ParsedReports for the comparison week (or None).
        comparison_date: ISO date string of the comparison week.

    Returns:
        AnalyticsResult — fully numeric, ready for report generation.
    """
    has_prior = previous is not None
    log.info("Calculating analytics (has_prior_data=%s)", has_prior)

    # ── Traffic Overview ──────────────────────────────────────────────────
    agg_tw = _agg_traffic(current.traffic_overview)
    agg_lw = _agg_traffic(previous.traffic_overview) if has_prior else None

    def _prev(key: str) -> Optional[float]:
        return agg_lw[key] if agg_lw else None

    sessions_kpi = _make_kpi("Sessions", agg_tw["sessions"], _prev("sessions"))
    users_kpi    = _make_kpi("Users", agg_tw["active_users"], _prev("active_users"))
    new_users_kpi = _make_kpi("New Users", agg_tw["new_users"], _prev("new_users"))
    dur_kpi = _make_kpi(
        "Avg Session", agg_tw["avg_session_duration"], _prev("avg_session_duration"),
        fmt_fn=_fmt_duration,
    )
    bounce_kpi = _make_kpi(
        "Bounce Rate", agg_tw["bounce_rate"], _prev("bounce_rate"),
        fmt_fn=lambda v: f"{v*100:.1f}%",
        lower_is_better=True,
    )

    # Daily session series
    by_date_tw: dict[str, float] = {}
    for r in current.traffic_overview:
        if r.date:
            by_date_tw[r.date] = by_date_tw.get(r.date, 0) + r.sessions

    by_date_lw: dict[str, float] = {}
    if has_prior:
        for r in previous.traffic_overview:
            if r.date:
                by_date_lw[r.date] = by_date_lw.get(r.date, 0) + r.sessions

    # Use day abbreviations as labels
    day_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    tw_vals = list(by_date_tw.values()) if by_date_tw else [agg_tw["sessions"]]
    lw_vals = list(by_date_lw.values()) if by_date_lw else ([agg_lw["sessions"]] if agg_lw else [])
    chart_labels = day_labels[:len(tw_vals)] if len(tw_vals) <= 7 else [str(i+1) for i in range(len(tw_vals))]

    log.info(
        "  Traffic: sessions=%s users=%s new=%s bounce=%.1f%% dur=%s",
        sessions_kpi.formatted, users_kpi.formatted, new_users_kpi.formatted,
        agg_tw["bounce_rate"] * 100, dur_kpi.formatted,
    )

    # ── Channel Grouping ──────────────────────────────────────────────────
    tw_channels: dict[str, float] = {r.channel: r.sessions for r in current.channel_grouping}
    lw_channels: dict[str, float] = {}
    if has_prior:
        lw_channels = {r.channel: r.sessions for r in previous.channel_grouping}

    all_channels = sorted(set(list(tw_channels.keys()) + list(lw_channels.keys())))
    channel_metrics: list[ChannelMetric] = []
    for ch in all_channels:
        tw_s = tw_channels.get(ch, 0.0)
        lw_s = lw_channels.get(ch, 0.0)
        channel_metrics.append(ChannelMetric(
            channel=ch,
            sessions_tw=tw_s,
            sessions_lw=lw_s,
            change=round(tw_s - lw_s, 1),
            pct_change=_pct_change(tw_s, lw_s) if has_prior else None,
        ))
    channel_metrics.sort(key=lambda x: x.sessions_tw, reverse=True)
    log.info("  Channels: %d entries", len(channel_metrics))

    # ── Search Queries ────────────────────────────────────────────────────
    lw_query_map: dict[str, SearchQueryRow] = {}
    if has_prior:
        for q in previous.search_queries:
            lw_query_map[q.query.lower()] = q

    # Weighted avg position
    tw_sq = current.search_queries
    total_clicks_tw = sum(q.clicks for q in tw_sq)
    total_impr_tw   = sum(q.impressions for q in tw_sq)
    site_ctr_tw     = total_clicks_tw / total_impr_tw if total_impr_tw > 0 else 0.0
    avg_pos_tw      = _weighted_avg(
        [q.avg_position for q in tw_sq],
        [q.impressions for q in tw_sq],
    )

    lw_sq = previous.search_queries if has_prior else []
    total_clicks_lw = sum(q.clicks for q in lw_sq)
    total_impr_lw   = sum(q.impressions for q in lw_sq)
    site_ctr_lw     = total_clicks_lw / total_impr_lw if total_impr_lw > 0 else 0.0
    avg_pos_lw      = _weighted_avg(
        [q.avg_position for q in lw_sq],
        [q.impressions for q in lw_sq],
    ) if lw_sq else None

    clicks_kpi = _make_kpi("Total Clicks", total_clicks_tw,
                           total_clicks_lw if has_prior else None)
    impr_kpi   = _make_kpi("Impressions", total_impr_tw,
                           total_impr_lw if has_prior else None)
    ctr_kpi    = _make_kpi("CTR", site_ctr_tw,
                           site_ctr_lw if has_prior else None,
                           fmt_fn=lambda v: f"{v*100:.2f}%")
    pos_kpi    = _make_kpi("Avg Position", avg_pos_tw, avg_pos_lw,
                           fmt_fn=lambda v: f"{v:.1f}",
                           lower_is_better=True)

    # Build query metrics (top 20 by clicks)
    query_metrics: list[SearchQueryMetric] = []
    for q in sorted(tw_sq, key=lambda x: x.clicks, reverse=True)[:20]:
        lw_q = lw_query_map.get(q.query.lower())
        impr_chg = _pct_change(q.impressions, lw_q.impressions) if lw_q else None
        query_metrics.append(SearchQueryMetric(
            query=q.query,
            clicks=q.clicks,
            impressions=q.impressions,
            ctr=q.ctr,
            avg_position=q.avg_position,
            impression_pct_change=impr_chg,
        ))

    growing_queries = [
        m for m in query_metrics
        if m.impression_pct_change is not None and m.impression_pct_change >= 10
    ]
    log.info(
        "  Search: clicks=%s impr=%s avgPos=%.1f growing_queries=%d",
        clicks_kpi.formatted, impr_kpi.formatted, avg_pos_tw, len(growing_queries),
    )

    # ── Landing Pages ─────────────────────────────────────────────────────
    lw_lp_map: dict[str, LandingPageRow] = {}
    if has_prior:
        for lp in previous.landing_pages:
            lw_lp_map[lp.page] = lp

    lp_metrics: list[LandingPageMetric] = []
    for lp in current.landing_pages:
        lw_lp = lw_lp_map.get(lp.page)
        lw_s  = lw_lp.sessions if lw_lp else 0.0
        lp_metrics.append(LandingPageMetric(
            page=lp.page,
            sessions_tw=lp.sessions,
            sessions_lw=lw_s,
            new_users=lp.new_users,
            change=round(lp.sessions - lw_s, 1),
            pct_change=_pct_change(lp.sessions, lw_s) if has_prior else None,
        ))

    lp_metrics_sorted = sorted(lp_metrics, key=lambda x: x.sessions_tw, reverse=True)
    top_landing = lp_metrics_sorted[:10]

    gainers = sorted(lp_metrics, key=lambda x: x.change, reverse=True)[:3]
    droppers = sorted(lp_metrics, key=lambda x: x.change)[:3]
    log.info("  Landing pages: %d total, top=%s", len(lp_metrics),
             top_landing[0].page if top_landing else "N/A")

    # ── Device Breakdown ──────────────────────────────────────────────────
    total_sessions_tw = agg_tw["sessions"] or 1.0  # avoid div/0
    lw_device_map: dict[str, float] = {}
    total_sessions_lw_dev = (agg_lw["sessions"] or 1.0) if agg_lw else 1.0
    if has_prior:
        for d in previous.device_breakdown:
            lw_device_map[d.device_category] = d.sessions

    device_metrics: list[DeviceMetric] = []
    for d in current.device_breakdown:
        share_tw = d.sessions / total_sessions_tw * 100
        lw_s = lw_device_map.get(d.device_category, 0.0)
        share_lw = lw_s / total_sessions_lw_dev * 100 if has_prior else 0.0
        device_metrics.append(DeviceMetric(
            device_category=d.device_category,
            sessions=d.sessions,
            share_pct=round(share_tw, 1),
            share_pct_lw=round(share_lw, 1),
            share_shift=round(share_tw - share_lw, 1),
        ))
    device_metrics.sort(key=lambda x: x.sessions, reverse=True)
    log.info("  Devices: %s", [(d.device_category, d.share_pct) for d in device_metrics])

    # ── Page Engagement ───────────────────────────────────────────────────
    lw_eng_map: dict[str, PageEngagementRow] = {}
    if has_prior:
        for pe in previous.page_engagement:
            lw_eng_map[pe.page] = pe

    # Site avg weighted by views
    all_eng = current.page_engagement
    site_avg_eng = _weighted_avg(
        [p.avg_engagement_time for p in all_eng],
        [p.views for p in all_eng],
    )

    eng_metrics: list[PageEngagementMetric] = []
    for pe in all_eng:
        lw_pe = lw_eng_map.get(pe.page)
        eng_chg = _pct_change(pe.avg_engagement_time, lw_pe.avg_engagement_time) if lw_pe else None
        eng_metrics.append(PageEngagementMetric(
            page=pe.page,
            avg_engagement_time=pe.avg_engagement_time,
            views=pe.views,
            engagement_time_change=eng_chg,
            vs_site_avg=round(pe.avg_engagement_time - site_avg_eng, 1),
        ))

    eng_by_time = sorted(eng_metrics, key=lambda x: x.avg_engagement_time, reverse=True)
    top_engaged = eng_by_time[:10]
    improved    = [m for m in eng_metrics if m.engagement_time_change is not None
                   and m.engagement_time_change >= 20]
    declined    = [m for m in eng_metrics if m.engagement_time_change is not None
                   and m.engagement_time_change <= -20]
    log.info(
        "  Engagement: site_avg=%s improved=%d declined=%d",
        _fmt_duration(site_avg_eng), len(improved), len(declined),
    )

    return AnalyticsResult(
        # Traffic
        sessions=sessions_kpi,
        users=users_kpi,
        new_users=new_users_kpi,
        avg_session_duration=dur_kpi,
        bounce_rate=bounce_kpi,
        sessions_by_day_tw=tw_vals,
        sessions_by_day_lw=lw_vals,
        sessions_day_labels=chart_labels,
        # Channel
        channels=channel_metrics,
        # Search
        total_clicks=clicks_kpi,
        total_impressions=impr_kpi,
        avg_position=pos_kpi,
        site_ctr=ctr_kpi,
        top_queries=query_metrics,
        growing_queries=growing_queries,
        # Landing pages
        top_landing_pages=top_landing,
        biggest_gainers=gainers,
        biggest_droppers=droppers,
        # Device
        devices=device_metrics,
        # Engagement
        site_avg_engagement_time=site_avg_eng,
        top_engaged_pages=top_engaged,
        engagement_improved=improved,
        engagement_declined=declined,
        # Meta
        has_prior_data=has_prior,
        comparison_week_date=comparison_date,
    )
