"""
interpret.py — LLM interpretation layer (structured placeholder).

Receives a fully-calculated AnalyticsResult and returns a structured
Interpretation. In this build, no external LLM API key is configured,
so the module generates a deterministic, data-driven narrative using
the calculated metrics — no fabrication, every sentence is traceable.

To enable real LLM interpretation in future, set ANTHROPIC_API_KEY
or OPENAI_API_KEY in the environment and uncomment the relevant section.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Optional

from analytics import AnalyticsResult

log = logging.getLogger(__name__)


@dataclass
class Interpretation:
    summary_paragraphs: list[str]   # 3–5 paragraphs of narrative
    key_findings: list[str]         # bullet-point findings
    anomalies: list[str]            # anything worth investigating
    action_item: str                # single recommended action


def _fmt_pct(v: Optional[float], suffix: str = "") -> str:
    if v is None:
        return "no prior data available for comparison"
    sign = "+" if v >= 0 else ""
    return f"{sign}{v:.1f}%{suffix}"


def _dir_word(v: Optional[float], lower_is_better: bool = False) -> str:
    if v is None:
        return "changed"
    if lower_is_better:
        return "improved" if v < 0 else "worsened"
    return "grew" if v > 0 else "declined"


def generate_interpretation(result: AnalyticsResult) -> Interpretation:
    """
    Build a structured interpretation from calculated metrics.

    Every sentence is derived directly from result fields.
    No arithmetic is performed here — only formatting and narrative assembly.
    """
    prior = result.has_prior_data
    comp  = f" (vs week of {result.comparison_week_date})" if result.comparison_week_date else ""

    # ── Paragraph 1: Overall traffic ──────────────────────────────────────
    sessions = result.sessions
    pct_s = _fmt_pct(sessions.pct_change)
    direction = "increased" if (sessions.pct_change or 0) > 0 else "decreased"
    if sessions.pct_change == 0 or sessions.pct_change is None:
        direction = "remained flat"

    p1_parts = [
        f"This week the site recorded **{sessions.formatted} sessions**{comp}.",
    ]
    if prior:
        p1_parts.append(
            f"That represents a {pct_s} change from the comparison period."
        )

    # Name the top channel
    if result.channels:
        top_ch = result.channels[0]
        p1_parts.append(
            f"The largest traffic source was **{top_ch.channel}** "
            f"with {int(top_ch.sessions_tw):,} sessions."
        )
        if prior and top_ch.pct_change is not None:
            chg_word = "gained" if top_ch.pct_change >= 0 else "lost"
            p1_parts.append(
                f"That channel {chg_word} {_fmt_pct(top_ch.pct_change)} week-over-week."
            )

    # Comment on quality signals
    bounce = result.bounce_rate
    dur    = result.avg_session_duration
    quality_parts = []
    if prior:
        if bounce.pct_change is not None:
            quality_parts.append(
                f"Bounce rate {_dir_word(bounce.pct_change, lower_is_better=True)} "
                f"({_fmt_pct(bounce.pct_change)}) to {bounce.formatted}."
            )
        if dur.pct_change is not None:
            quality_parts.append(
                f"Average session duration {_dir_word(dur.pct_change)} "
                f"({_fmt_pct(dur.pct_change)}) to {dur.formatted}."
            )
    if quality_parts:
        p1_parts.append(" ".join(quality_parts))

    p1 = " ".join(p1_parts)

    # ── Paragraph 2: Search momentum ─────────────────────────────────────
    clicks = result.total_clicks
    impr   = result.total_impressions
    pos    = result.avg_position

    p2_parts = [
        f"From Search Console: the site received **{clicks.formatted} organic clicks** "
        f"from **{impr.formatted} impressions** this week."
    ]
    if prior:
        p2_parts.append(
            f"Clicks {_dir_word(clicks.pct_change)} {_fmt_pct(clicks.pct_change)} "
            f"and impressions {_dir_word(impr.pct_change)} {_fmt_pct(impr.pct_change)}."
        )
        if pos.pct_change is not None:
            pos_word = "improved" if pos.pct_change < 0 else "dropped"
            p2_parts.append(
                f"Average search position {pos_word} from "
                f"{pos.value + (pos.pct_change * pos.value / 100):.1f} to {pos.formatted}."
            )

    if result.growing_queries:
        top_gq = result.growing_queries[:3]
        qnames = ", ".join(f'"{q.query}"' for q in top_gq)
        p2_parts.append(
            f"{len(result.growing_queries)} quer{'y' if len(result.growing_queries)==1 else 'ies'} "
            f"gained 10%+ in impressions this week: {qnames}."
        )
    else:
        p2_parts.append(
            "No individual queries showed 10%+ impression growth this week."
        )

    p2 = " ".join(p2_parts)

    # ── Paragraph 3: Content performance ─────────────────────────────────
    p3_parts = []
    if result.top_landing_pages:
        top_lp = result.top_landing_pages[0]
        p3_parts.append(
            f"The most-visited landing page was **{top_lp.page}** "
            f"with {int(top_lp.sessions_tw):,} sessions."
        )
    if result.biggest_gainers:
        gainer = result.biggest_gainers[0]
        if gainer.change > 0:
            p3_parts.append(
                f"The biggest session gain was **{gainer.page}** "
                f"(+{int(gainer.change):,} sessions, {_fmt_pct(gainer.pct_change)})."
            )
    if result.biggest_droppers:
        dropper = result.biggest_droppers[0]
        if dropper.change < 0:
            p3_parts.append(
                f"The sharpest drop was **{dropper.page}** "
                f"({int(dropper.change):,} sessions, {_fmt_pct(dropper.pct_change)})."
            )
    if result.top_engaged_pages:
        best_eng = result.top_engaged_pages[0]
        mins = int(best_eng.avg_engagement_time) // 60
        secs = int(best_eng.avg_engagement_time) % 60
        p3_parts.append(
            f"The most engaging page was **{best_eng.page}** "
            f"with an average engagement time of {mins}m {secs}s."
        )

    p3 = " ".join(p3_parts) if p3_parts else (
        "Content performance data was not available for this period."
    )

    # ── Paragraph 4: Devices ─────────────────────────────────────────────
    p4_parts = []
    for d in result.devices:
        if d.device_category.lower() == "mobile":
            p4_parts.append(
                f"Mobile accounted for **{d.share_pct:.1f}%** of sessions."
            )
            if prior and d.share_shift != 0:
                shift_word = "up" if d.share_shift > 0 else "down"
                p4_parts.append(
                    f"Mobile share moved {shift_word} {abs(d.share_shift):.1f} percentage points."
                )
    p4 = " ".join(p4_parts) if p4_parts else ""

    # ── Action item ───────────────────────────────────────────────────────
    action = _pick_action_item(result)

    # ── Key findings ──────────────────────────────────────────────────────
    findings: list[str] = []
    if prior:
        findings.append(
            f"Sessions {_dir_word(sessions.pct_change)} {_fmt_pct(sessions.pct_change)} to {sessions.formatted}."
        )
    if result.growing_queries:
        findings.append(
            f"{len(result.growing_queries)} search quer{'y' if len(result.growing_queries)==1 else 'ies'} gained 10%+ in impressions."
        )
    if result.biggest_gainers and result.biggest_gainers[0].change > 0:
        g = result.biggest_gainers[0]
        findings.append(f"Top gaining page: {g.page} (+{int(g.change):,} sessions).")
    if result.engagement_improved:
        findings.append(
            f"{len(result.engagement_improved)} page(s) saw 20%+ improvement in engagement time."
        )
    if not findings:
        findings.append("Baseline week — no prior data for comparison.")

    # ── Anomalies ─────────────────────────────────────────────────────────
    anomalies: list[str] = []
    if result.biggest_droppers and result.biggest_droppers[0].pct_change is not None:
        d = result.biggest_droppers[0]
        if d.pct_change <= -30:
            anomalies.append(
                f"Significant traffic drop on {d.page} ({_fmt_pct(d.pct_change)}). "
                "Check for content removal, URL changes, or indexing issues."
            )
    if result.engagement_declined:
        anomalies.append(
            f"{len(result.engagement_declined)} page(s) saw 20%+ decline in engagement time. "
            "Consider reviewing content quality or page load speed."
        )
    # Check for mobile share spike
    for d in result.devices:
        if d.device_category.lower() == "mobile" and d.share_shift >= 10:
            anomalies.append(
                f"Mobile share jumped +{d.share_shift:.1f}pp. "
                "Verify mobile rendering on recently published pages."
            )

    paragraphs = [p for p in [p1, p2, p3, p4] if p]

    return Interpretation(
        summary_paragraphs=paragraphs,
        key_findings=findings,
        anomalies=anomalies,
        action_item=action,
    )


def _pick_action_item(result: AnalyticsResult) -> str:
    """Pick the single most actionable item from the data."""
    # Priority 1: a growing query with no dedicated page
    if result.growing_queries:
        q = result.growing_queries[0]
        return (
            f'The query "{q.query}" gained {_fmt_pct(q.impression_pct_change)} in impressions this week. '
            f"Consider creating or optimising a page that targets this topic."
        )

    # Priority 2: top landing page with high bounce rate
    # (we'd need per-page bounce rate — use session duration as proxy)
    if result.top_landing_pages:
        top = result.top_landing_pages[0]
        return (
            f"Your top landing page **{top.page}** received {int(top.sessions_tw):,} sessions. "
            "Review it for clear calls-to-action and ensure the content matches search intent."
        )

    # Priority 3: any engagement decline
    if result.engagement_declined:
        d = result.engagement_declined[0]
        return (
            f"Engagement time on {d.page} declined {_fmt_pct(d.engagement_time_change)}. "
            "Check page load speed and content freshness."
        )

    # Fallback
    return (
        "Review this week's top landing pages and ensure each one has a "
        "clear next step for visitors (subscribe, contact, or read more)."
    )
