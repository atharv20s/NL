---
name: weekly-analytics-report
description: >-
  Use this skill when the user invokes /weekly-analytics-report or asks to
  generate their weekly Google Analytics and Search Console report. This skill
  runs the full end-to-end pipeline: locates CSV files (from Gmail or local
  sample data), validates and identifies each report type, parses them
  deterministically, calculates all week-over-week metrics in code (no LLM
  arithmetic), generates a structured interpretation, renders a self-contained
  dark-mode HTML report with Chart.js charts, saves everything to a dated
  folder, and prints a concise quick-stats recap.
---

# Weekly Analytics Report Skill

> **Trigger**: `/weekly-analytics-report`
>
> Run every Monday after GA4 CSV reports arrive. Type the trigger and the
> full 8-stage pipeline runs automatically.

---

## Quick Reference

| Mode | Command |
|------|---------|
| Dry-run (sample data) | `python scripts/main.py --mode dry-run` |
| Dry-run with prior data | `python scripts/main.py --mode dry-run --previous-dir sample_data/previous_week` |
| Live (Gmail) | `python scripts/main.py --mode live` |
| Gmail auth setup | `python scripts/main.py --mode live --auth-only` |
| Custom run date | `python scripts/main.py --mode dry-run --date 2026-09-01` |
| Verbose logging | `python scripts/main.py --mode dry-run --verbose` |

---

## Pipeline Stages

```
1. Ingestion   → ingest.py    (Gmail API or local CSV files)
2. Validation  → validate.py  (identify report types, check columns)
3. Persist raw → persist.py   (save original CSVs to dated folder)
4. Parsing     → parse.py     (typed Python dataclasses, no LLM)
5. Comparison  → compare.py   (find previous run, load prior data)
6. Analytics   → analytics.py (all arithmetic — deterministic)
7. Interpret   → interpret.py (narrative from calculated metrics)
8. Report      → report_gen.py + persist.py (HTML + metadata)
```

---

## Prerequisites

Before running in **live mode**, complete these steps once:

1. Set up Google Analytics 4 for your site.
2. Link Google Search Console to your GA4 property.
3. Schedule the 6 CSV reports in GA4 (see [report-setup-guide.md](../../skills/weekly-analytics-report/references/report-setup-guide.md)).
4. Set up Gmail OAuth2 credentials:
   - Enable Gmail API at <https://console.cloud.google.com>
   - Create **Desktop app** OAuth2 credentials → download `credentials.json`
   - Place at: `C:\Users\athar\analytics-reports\.gmail-credentials.json`
   - Run: `python scripts/main.py --mode live --auth-only` (one-time browser auth)

---

## When Running This Skill

1. Confirm mode: ask the user if they want `dry-run` (test with sample data) or `live` (real Gmail).
2. Run the appropriate command.
3. The pipeline logs every stage — show the output to the user.
4. Open the HTML report path printed at the end.
5. Present the quick-stats recap from the log output.

---

## References

- [report-setup-guide.md](../../skills/weekly-analytics-report/references/report-setup-guide.md) — GA4 report configuration
- [csv-column-reference.md](../../skills/weekly-analytics-report/references/csv-column-reference.md) — CSV column signatures
- [metrics-reference.md](../../skills/weekly-analytics-report/references/metrics-reference.md) — Metric formulas
- [README.md](../../README.md) — Full setup documentation
