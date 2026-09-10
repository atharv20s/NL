# Weekly Analytics Report System

A fully working end-to-end pipeline that turns scheduled Google Analytics 4
CSV email attachments into a rich, self-contained HTML report — every Monday,
automatically.

---

## What It Does

```
Google Analytics / Search Console
↓  (6 scheduled CSV exports, delivered Monday via email)
Gmail inbox
↓  ingest.py  — finds and downloads attachments (or reads local CSVs)
↓  validate.py — identifies each report type, checks required columns
↓  persist.py  — saves raw CSVs to ~/analytics-reports/YYYY-MM-DD/raw/
↓  parse.py    — deterministic typed parsing (no LLM arithmetic)
↓  compare.py  — finds the most recent previous run for WoW comparison
↓  analytics.py — all metric calculations (weighted avgs, % changes, ranks)
↓  interpret.py — data-driven narrative (traceable to calculated metrics)
↓  report_gen.py — Jinja2 HTML report with Chart.js charts
↓  persist.py  — saves report + run-metadata.json
↓
~/analytics-reports/YYYY-MM-DD/
   ├── raw/   (6 original CSV files)
   └── report/weekly-report-YYYY-MM-DD.html
```

---

## Project Structure

```
T1/
├── .agents/skills/weekly-analytics-report/SKILL.md  ← Antigravity trigger
├── skills/weekly-analytics-report/                  ← Reference docs (preserved)
│   ├── references/
│   │   ├── report-setup-guide.md
│   │   ├── csv-column-reference.md
│   │   └── metrics-reference.md
│   └── resources/report-template.html
├── scripts/
│   ├── main.py         ← Orchestrator (run this)
│   ├── ingest.py       ← Gmail API or local file mode
│   ├── validate.py     ← CSV identification + column validation
│   ├── parse.py        ← Typed CSV parsing
│   ├── analytics.py    ← Deterministic metric calculations
│   ├── compare.py      ← Historical previous-run discovery
│   ├── interpret.py    ← Data-driven narrative generation
│   ├── report_gen.py   ← Jinja2 HTML rendering
│   └── persist.py      ← Idempotent file persistence
├── templates/
│   └── report.html.j2  ← Jinja2 HTML template
├── sample_data/
│   ├── current_week/   ← 6 sample CSVs for dry-run testing
│   └── previous_week/  ← Previous week CSVs (enables WoW comparison)
├── tests/
│   ├── conftest.py
│   ├── test_validate.py
│   ├── test_parse.py
│   ├── test_analytics.py
│   ├── test_compare.py
│   └── test_report_gen.py
├── requirements.txt
└── README.md
```

---

## Setup

### 1. Install Dependencies

```powershell
cd C:\Users\athar\OneDrive\Desktop\shikshita-m8m\T1
pip install -r requirements.txt
```

### 2. Run the Test Suite

```powershell
cd C:\Users\athar\OneDrive\Desktop\shikshita-m8m\T1
pytest tests/ -v
```

All tests should pass before running the live pipeline.

### 3. Dry-Run (No Gmail Required)

Test the entire pipeline using the bundled sample data:

```powershell
# First run (no comparison data):
python scripts/main.py --mode dry-run

# With week-over-week comparison:
python scripts/main.py --mode dry-run --previous-dir sample_data/previous_week

# Verbose debug output:
python scripts/main.py --mode dry-run --previous-dir sample_data/previous_week --verbose
```

The generated report will be at:
```
C:\Users\athar\analytics-reports\YYYY-MM-DD\report\weekly-report-YYYY-MM-DD.html
```

---

## Gmail / Live Mode Setup

> **Only required if you want the pipeline to read real emails automatically.**

### Step 1: Enable Gmail API

1. Go to <https://console.cloud.google.com>
2. Create or select a project.
3. Navigate to **APIs & Services → Library** → search "Gmail API" → Enable.

### Step 2: Create OAuth2 Credentials

1. **APIs & Services → Credentials → Create Credentials → OAuth client ID**
2. Application type: **Desktop app**
3. Download the JSON file as `credentials.json`
4. Move it to:
   ```
   C:\Users\athar\analytics-reports\.gmail-credentials.json
   ```

### Step 3: Authenticate (One-Time)

```powershell
python scripts/main.py --mode live --auth-only
```

This opens a browser window. Sign in with the Google account that receives
the scheduled GA4 emails. The token is cached at:
```
C:\Users\athar\analytics-reports\.gmail-token.json
```

You never need to do this again unless you revoke access.

### Step 4: Run Live

```powershell
python scripts/main.py --mode live
```

---

## Google Analytics 4 Scheduled Reports Setup

Configure these 6 scheduled reports in GA4 (weekly, Monday delivery):

| # | Report | GA4 Path | Key Columns |
|---|--------|----------|-------------|
| 1 | Traffic Overview | Reports → Acquisition → Overview | Date, Sessions, Active Users, New Users, Bounce Rate, Avg Session Duration |
| 2 | Channel Grouping | Reports → Acquisition → Traffic Acquisition | Session default channel group, Sessions |
| 3 | Landing Pages | Reports → Engagement → Landing Page | Landing page + query string, Sessions, New Users |
| 4 | Search Queries | Reports → Acquisition → Search Console → Queries | Query, Clicks, Impressions, CTR, Average Position |
| 5 | Device Breakdown | Reports → User → Tech (by Device category) | Device category, Sessions |
| 6 | Page Engagement | Reports → Engagement → Pages and Screens | Page path + screen class, Views, Average Engagement Time |

For detailed instructions, see:
[skills/weekly-analytics-report/references/report-setup-guide.md](skills/weekly-analytics-report/references/report-setup-guide.md)

---

## Output Folder Structure

Each run creates:

```
C:\Users\athar\analytics-reports\
└── 2026-09-08\
    ├── raw\
    │   ├── traffic_overview.csv
    │   ├── channel_grouping.csv
    │   ├── landing_pages.csv
    │   ├── search_queries.csv
    │   ├── device_breakdown.csv
    │   └── page_engagement.csv
    ├── report\
    │   └── weekly-report-2026-09-08.html
    └── run-metadata.json
```

Running the same date again **overwrites** existing files (idempotent).

---

## Antigravity Skill Invocation

The skill is registered at `.agents/skills/weekly-analytics-report/SKILL.md`.
In Antigravity IDE, type:

```
/weekly-analytics-report
```

The agent will ask you for the mode (dry-run or live) and run the pipeline.

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `No .csv files found` | Check `sample_data/current_week/` exists or that Gmail received reports |
| `Gmail credentials not found` | Copy `credentials.json` to `C:\Users\athar\analytics-reports\.gmail-credentials.json` |
| `Could not locate header row` | The CSV has an unusual format — check `csv-column-reference.md` |
| `Token has been expired or revoked` | Delete `.gmail-token.json` and re-run `--auth-only` |
| Report has no WoW comparison | Run with `--previous-dir sample_data/previous_week` or wait until week 2 |
| `No matching emails found` | Confirm scheduled reports are configured and Monday has passed |
| Tests fail | Run `pip install -r requirements.txt` first |

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ANALYTICS_SITE_NAME` | `My Site` | Site name shown in the report header |

---

## Running Tests

```powershell
# All tests:
pytest tests/ -v

# Specific module:
pytest tests/test_validate.py -v
pytest tests/test_analytics.py -v

# With coverage:
pip install pytest-cov
pytest tests/ --cov=scripts --cov-report=term-missing
```
