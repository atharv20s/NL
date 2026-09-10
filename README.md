# Weekly Analytics Report Skill for Claude

A Claude skill that turns scheduled Google Analytics 4 & Search Console CSV emails into an interactive, self-contained **Artifact report** so you can actually see what's going on in your business.

Based on the workflow by [Wyndo](https://substack.com/@wyndo) (*"My Claude Skill for Automated Weekly Google Analytics Reports"*).

---

## What It Does

Every Monday, scheduled CSV reports arrive in your inbox. Instead of opening 6 spreadsheets and manually calculating week-over-week changes, upload them to Claude. This skill will:

1. **Identify and Validate the 6 Reports** — automatically maps each file by column headers and signatures (traffic overview, channels, landing pages, search queries, devices, page engagement).
2. **Perform Deterministic Calculations** — calculates week-over-week % changes, weighted search positions, channel shifts, and device breakdown with exact arithmetic (zero hallucinations).
3. **Isolate What Matters** — surfaces your biggest landing page gainers, queries gaining search momentum (+10% impressions), and traffic drops.
4. **Generate a Visual Artifact Report** — renders a self-contained, responsive dark-mode HTML dashboard with embedded Chart.js charts (daily traffic line chart, channel bars, device donut, KPI cards, and data tables).
5. **Summarize the Story** — provides an executive narrative explaining *why* traffic moved and suggests one high-leverage action item for the week.

---

## The 6 Standard Reports

| # | Report | Questions Answered | Key Dimensions & Metrics |
|---|--------|--------------------|--------------------------|
| 1 | **Traffic Overview** | Did traffic change and did quality move with it? | Sessions, Users, Bounce Rate, Avg Duration |
| 2 | **Channel Grouping** | Which channel explains the shift? | Organic Search, Direct, Email, Social, Referral |
| 3 | **Landing Pages** | Which pages are bringing in new readers? | Page path, Sessions, New Users |
| 4 | **Search Queries** | What are people searching for and what is gaining momentum? | Query, Clicks, Impressions, CTR, Position |
| 5 | **Device Breakdown** | How is the desktop vs. mobile ratio shifting? | Device Category, Sessions, % Share |
| 6 | **Page Engagement** | Are visitors sticking around and reading? | Page path, Average Engagement Time |

> **Graceful Fallback**: If fewer than 6 reports are provided, the skill automatically adapts and produces a *General Movement* report using the available data.

---

## Installation

### Option 1: Claude.ai (Skills / Projects)

1. Go to **Settings → Skills** (or create a **Project**) in [Claude.ai](https://claude.ai).
2. Create a new skill named `weekly-analytics-report`.
3. Paste the contents of [`SKILL.md`](./SKILL.md) into the skill prompt editor.
4. Upload [`resources/report-template.html`](./resources/report-template.html), [`references/csv-column-reference.md`](./references/csv-column-reference.md), and [`references/metrics-reference.md`](./references/metrics-reference.md) to Project Knowledge.
5. Save.

### Option 2: Claude Code CLI

Copy this skill folder directly into your Claude skills directory:

```bash
# Clone the repository
git clone https://github.com/atharv20s/NL.git weekly-analytics-report-skill

# Project-level install:
mkdir -p .claude/skills
cp -r weekly-analytics-report-skill .claude/skills/weekly-analytics-report

# Global install:
mkdir -p ~/.claude/skills
cp -r weekly-analytics-report-skill ~/.claude/skills/weekly-analytics-report
```

---

## How to Use It

Once installed, simply drag and drop your scheduled CSV files into Claude and trigger the skill:

> "Here are this week's scheduled GA4 and Search Console CSV exports. Please run `/weekly-analytics-report` and generate my weekly dashboard Artifact."

If you also have last week's CSVs, attach both:

> "I have attached this week's 6 CSV reports and last week's 6 CSV reports. Run `/weekly-analytics-report` to compare week-over-week performance."

Claude will process the files and generate the visual interactive report inside an Artifact.

---

## Repo Structure

```text
NL/
├── SKILL.md                          # The core skill definition — install this in Claude
├── README.md                         # Repository documentation
├── evals/
│   └── evals.json                    # Test evaluation cases for validating the skill
├── references/
│   ├── report-setup-guide.md         # How to schedule the 6 GA4 reports in Google Analytics
│   ├── csv-column-reference.md       # Exact column signatures & dimensions for each CSV
│   └── metrics-reference.md          # Formula definitions (WoW changes, weighted position, shares)
├── resources/
│   └── report-template.html          # Base dark-mode HTML dashboard template (Chart.js)
└── examples/
    ├── current_week/                 # 6 realistic sample CSV exports
    ├── previous_week/                # 6 previous week CSV exports for WoW comparison
    └── example-report.html           # Rendered example HTML artifact report
```

---

## Setup Guide for Google Analytics

Follow [references/report-setup-guide.md](./references/report-setup-guide.md) for step-by-step instructions on configuring and scheduling the 6 GA4 reports to arrive in your inbox automatically every Monday.

---

## Contributing

Pull requests and contributions are welcome:
- Additional evaluation cases in `evals/evals.json`
- Alternative report templates (e.g. light theme, executive 1-page PDF layout)
- Support for additional acquisition channels or ecommerce metrics
