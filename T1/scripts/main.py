"""
main.py — Weekly Analytics Report orchestrator.

Usage:
  python scripts/main.py --mode dry-run [--data-dir sample_data] [--date YYYY-MM-DD]
  python scripts/main.py --mode live    [--date YYYY-MM-DD] [--auth-only]
  python scripts/main.py --mode dry-run --previous-dir sample_data/previous_week

Each stage is logged with a clear prefix so you can see exactly what happened.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import tempfile
from datetime import date, datetime
from pathlib import Path

# Force UTF-8 stdout on Windows to avoid cp1252 UnicodeEncodeError
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ── Path setup (so scripts/ can import siblings) ──────────────────────────────
SCRIPTS_DIR = Path(__file__).parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from ingest   import ingest_local, ingest_gmail, authenticate_only, IngestedFile
from validate import validate_files, ReportType
from parse    import parse_reports
from analytics import calculate
from compare  import find_previous_run
from interpret import generate_interpretation
from report_gen import generate_report
from persist  import setup_run_directory, save_raw_csvs, write_report, write_metadata, RunMetadata

# ── Constants ─────────────────────────────────────────────────────────────────
DATA_ROOT   = Path.home() / "analytics-reports"
SITE_NAME   = os.environ.get("ANALYTICS_SITE_NAME", "My Site")


# ── Logging setup ─────────────────────────────────────────────────────────────

def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    fmt   = "%(asctime)s  %(levelname)-8s  %(message)s"
    logging.basicConfig(level=level, format=fmt, datefmt="%H:%M:%S", stream=sys.stdout)


# ── Stage runners ─────────────────────────────────────────────────────────────

def _stage(name: str) -> None:
    log = logging.getLogger(__name__)
    log.info("")
    log.info("=" * 46)
    log.info("  STAGE: %s", name)
    log.info("=" * 46)


def run(args: argparse.Namespace) -> int:
    log = logging.getLogger(__name__)
    run_date = args.date or date.today().isoformat()
    data_root = Path(args.data_root) if args.data_root else DATA_ROOT

    log.info("Weekly Analytics Report")
    log.info("  Mode:       %s", args.mode)
    log.info("  Run date:   %s", run_date)
    log.info("  Data root:  %s", data_root)

    # ── Auth-only shortcut ────────────────────────────────────────────────
    if getattr(args, "auth_only", False):
        _stage("Gmail Authentication Only")
        authenticate_only()
        log.info("✓ Authentication complete.")
        return 0

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # STAGE 1: Ingestion
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    _stage("1 / 8 — Ingestion")

    ingested: list[IngestedFile] = []

    if args.mode == "dry-run":
        source_dir = args.data_dir or "sample_data/current_week"
        log.info("Dry-run mode — reading from: %s", source_dir)
        try:
            ingested = ingest_local(source_dir)
        except FileNotFoundError as e:
            log.error("Ingestion failed: %s", e)
            return 1

    elif args.mode == "live":
        # Temporary dir for Gmail attachments (persist.py copies them to dated folder later)
        tmp_dir = Path(tempfile.mkdtemp(prefix="analytics_ingest_"))
        log.info("Live mode — downloading Gmail attachments to: %s", tmp_dir)
        try:
            ingested = ingest_gmail(tmp_dir)
        except FileNotFoundError as e:
            log.error("Gmail credentials not found: %s", e)
            log.error("Run: python scripts/main.py --mode live --auth-only   (then retry)")
            return 1
        except Exception as e:
            log.error("Gmail ingestion failed: %s", e)
            return 1

    if not ingested:
        log.error("No CSV files found. Aborting.")
        return 1

    log.info("Ingested %d file(s):", len(ingested))
    for f in ingested:
        log.info("  [%s] %s", f.source, f.original_filename)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # STAGE 2: Validation
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    _stage("2 / 8 — Validation")

    raw_paths = [f.path for f in ingested]
    validation = validate_files(raw_paths)

    log.info("Validation result:")
    log.info("  ✓ Valid reports: %d", len(validation.validated))
    for vr in validation.validated:
        log.info("    %-22s  rows=%-4d  file=%s",
                 vr.report_type.value, vr.row_count, vr.original_filename)

    missing = validation.missing_report_types()
    if missing:
        log.warning("  ⚠ Missing standard reports: %s", [m.value for m in missing])
        log.warning("    The report will run in partial/General Movement mode.")

    if validation.errors:
        log.warning("  ✗ Validation errors (%d):", len(validation.errors))
        for err in validation.errors:
            log.warning("    %s", err)

    if not validation.validated:
        log.error("No valid reports found — cannot continue.")
        return 1

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # STAGE 3: Persistence — save raw CSVs
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    _stage("3 / 8 — Save Raw CSVs")

    raw_dir, report_dir = setup_run_directory(data_root, run_date)
    saved_paths = save_raw_csvs(raw_paths, raw_dir)
    log.info("Saved %d raw CSV(s) to: %s", len(saved_paths), raw_dir)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # STAGE 4: Parsing
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    _stage("4 / 8 — Parse CSVs")

    current_parsed = parse_reports(validation.validated)
    if current_parsed.parse_warnings:
        for w in current_parsed.parse_warnings:
            log.warning("  Parse warning: %s", w)

    row_counts = {
        "traffic_overview": len(current_parsed.traffic_overview),
        "channel_grouping":  len(current_parsed.channel_grouping),
        "landing_pages":     len(current_parsed.landing_pages),
        "search_queries":    len(current_parsed.search_queries),
        "device_breakdown":  len(current_parsed.device_breakdown),
        "page_engagement":   len(current_parsed.page_engagement),
    }
    log.info("Row counts: %s", json.dumps(row_counts, indent=2))

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # STAGE 5: Historical comparison
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    _stage("5 / 8 — Historical Comparison")

    # Override previous dir if supplied
    previous_parsed = None
    comparison_date = None

    if getattr(args, "previous_dir", None):
        log.info("Using explicit previous-week dir: %s", args.previous_dir)
        prev_val = validate_files([str(p) for p in Path(args.previous_dir).glob("*.csv")])
        if prev_val.validated:
            previous_parsed = parse_reports(prev_val.validated)
            comparison_date = "(manual)"
        else:
            log.warning("No valid CSVs in previous_dir. Skipping comparison.")
    else:
        run_date_obj = datetime.strptime(run_date, "%Y-%m-%d").date()
        prev_run = find_previous_run(data_root, run_date_obj)
        if prev_run:
            previous_parsed = prev_run.parsed
            comparison_date = prev_run.date_str
            log.info("Comparison period: %s", comparison_date)
        else:
            log.info("First run — no comparison period available.")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # STAGE 6: Deterministic analytics
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    _stage("6 / 8 — Analytics Calculations")

    analytics_result = calculate(current_parsed, previous_parsed, comparison_date)

    log.info("Key metrics:")
    log.info("  Sessions:     %s (%s)", analytics_result.sessions.formatted,
             analytics_result.sessions.change_formatted)
    log.info("  Clicks:       %s (%s)", analytics_result.total_clicks.formatted,
             analytics_result.total_clicks.change_formatted)
    log.info("  Impressions:  %s (%s)", analytics_result.total_impressions.formatted,
             analytics_result.total_impressions.change_formatted)
    log.info("  Avg Position: %s (%s)", analytics_result.avg_position.formatted,
             analytics_result.avg_position.change_formatted)
    log.info("  Channels:     %d", len(analytics_result.channels))
    log.info("  Top queries:  %d", len(analytics_result.top_queries))
    log.info("  Growing Q:    %d", len(analytics_result.growing_queries))

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # STAGE 7: LLM interpretation (structured placeholder)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    _stage("7 / 8 — Interpretation")

    interpretation = generate_interpretation(analytics_result)

    log.info("Action item: %s", interpretation.action_item[:100])
    log.info("Key findings: %d  |  Anomalies: %d",
             len(interpretation.key_findings), len(interpretation.anomalies))

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # STAGE 8: Report generation + persistence
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    _stage("8 / 8 — Report Generation & Persistence")

    html = generate_report(
        result=analytics_result,
        interpretation=interpretation,
        week_date=run_date,
        data_root=str(data_root),
        site_name=SITE_NAME,
    )

    report_path = write_report(html, report_dir, run_date)

    metadata = RunMetadata(
        run_date=run_date,
        generated_at=datetime.now().isoformat(),
        comparison_date=comparison_date,
        mode=args.mode,
        input_files=[f.original_filename for f in ingested],
        report_types_found=[vr.report_type.value for vr in validation.validated],
        row_counts=row_counts,
        report_path=str(report_path),
        warnings=(
            [str(e) for e in validation.errors] +
            current_parsed.parse_warnings
        ),
    )
    meta_path = write_metadata(metadata, data_root / run_date)

    # ── Final summary ─────────────────────────────────────────────────────
    log.info("")
    log.info("=" * 50)
    log.info("[DONE] Weekly Analytics Report Complete")
    log.info("=" * 50)
    log.info("")
    log.info("  Week of:    %s", run_date)
    if comparison_date:
        log.info("  Compared:   %s", comparison_date)
    else:
        log.info("  Compared:   (first run -- no prior data)")
    log.info("")
    log.info("  Saved to: %s", data_root / run_date)
    log.info("     +-- raw/   (%d CSV file(s))", len(saved_paths))
    log.info("     +-- report/weekly-report-%s.html", run_date)
    log.info("")
    log.info("  Quick Stats:")
    log.info("     Sessions:       %s  (%s)", analytics_result.sessions.formatted,
             analytics_result.sessions.change_formatted)
    log.info("     Users:          %s  (%s)", analytics_result.users.formatted,
             analytics_result.users.change_formatted)
    log.info("     Organic Clicks: %s  (%s)", analytics_result.total_clicks.formatted,
             analytics_result.total_clicks.change_formatted)
    log.info("     Avg Position:   %s  (%s)", analytics_result.avg_position.formatted,
             analytics_result.avg_position.change_formatted)
    if analytics_result.top_queries:
        tq = analytics_result.top_queries[0]
        log.info("     Top Query:      \"%s\" (%d clicks)", tq.query, int(tq.clicks))
    if analytics_result.top_landing_pages:
        tlp = analytics_result.top_landing_pages[0]
        log.info("     Top Page:       %s (%d sessions)", tlp.page, int(tlp.sessions_tw))
    log.info("")
    log.info("  Key Insight: %s", interpretation.key_findings[0] if interpretation.key_findings else "N/A")
    log.info("")
    log.info("  Report: file://%s", report_path)
    log.info("")

    return 0


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Weekly Google Analytics + Search Console report generator.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run with bundled sample data:
  python scripts/main.py --mode dry-run

  # Dry run with custom sample data, comparing to a previous folder:
  python scripts/main.py --mode dry-run --data-dir sample_data/current_week \\
         --previous-dir sample_data/previous_week

  # Live run (requires Gmail credentials):
  python scripts/main.py --mode live

  # Authenticate Gmail only (one-time setup):
  python scripts/main.py --mode live --auth-only

  # Specify a custom analytics data root:
  python scripts/main.py --mode dry-run --data-root C:/my/reports
        """
    )
    parser.add_argument("--mode", choices=["dry-run", "live"], default="dry-run",
                        help="Ingestion mode (default: dry-run)")
    parser.add_argument("--date", metavar="YYYY-MM-DD",
                        help="Override the run date (default: today)")
    parser.add_argument("--data-dir", metavar="PATH",
                        help="[dry-run] Directory containing current week CSV files")
    parser.add_argument("--previous-dir", metavar="PATH",
                        help="[dry-run] Directory containing previous week CSV files (skips auto-discovery)")
    parser.add_argument("--data-root", metavar="PATH",
                        help=f"Root directory for analytics output (default: {DATA_ROOT})")
    parser.add_argument("--auth-only", action="store_true",
                        help="[live] Authenticate Gmail and exit (one-time setup)")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Enable debug logging")

    args = parser.parse_args()
    setup_logging(args.verbose)

    sys.exit(run(args))


if __name__ == "__main__":
    main()
