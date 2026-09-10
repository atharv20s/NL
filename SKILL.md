---
name: weekly-analytics-report
description: >-
  Use this skill when the user invokes /weekly-analytics-report or asks to
  generate their weekly Google Analytics and Search Console report. This skill
  locates the six scheduled CSV email attachments (traffic overview, channel
  grouping, landing pages, search queries, device breakdown, and page
  engagement) in the user's Gmail inbox, reads and compares them to the
  previous week's saved data, generates a rich visual HTML Artifact report
  (with charts, tables, and a written summary), and saves the raw CSVs plus the
  finished report in a dated folder for long-term trend tracking.
---

# Weekly Analytics Report Skill

> **Trigger**: `/weekly-analytics-report`
>
> Run every Monday after the scheduled Google Analytics and Search Console CSV
> emails arrive. Reads the CSV attachments, compares them to last week, creates
> a visual Artifact report, and saves everything in a dated folder.

---

## Prerequisites Checklist

Before running, silently confirm these conditions are met. If any are missing,
tell the user which step they need to complete first and stop.

- [ ] Google Analytics is collecting data for the user's site.
- [ ] Google Search Console is verified and linked to the GA4 property.
- [ ] Six scheduled CSV reports are configured in Google Analytics and are sent
      to the user's Gmail inbox every Monday. See
      [report-setup-guide.md](./references/report-setup-guide.md) for the exact
      report specs.
- [ ] The AI has Gmail access (e.g., Google Workspace CLI, Gmail MCP, or the
      Claude Gmail tool). If Gmail access is unavailable, ask the user to
      forward or paste the CSV files manually.
- [ ] A base data directory exists: `~/analytics-reports/`. Create it
      automatically if it does not exist.

---

## Step 1 — Locate This Week's CSV Emails

Search the Gmail inbox for emails matching **all** of the following:

| Field   | Value                                                                 |
|---------|-----------------------------------------------------------------------|
| From    | `google-analytics-noreply@google.com` OR `analytics-noreply@google.com` |
| Subject | Contains `"Scheduled report"` OR `"Google Analytics Report"`         |
| Date    | Received within the last **7 days**                                   |
| Has     | `.csv` attachment                                                    |

Retrieve **all matching emails** and extract their CSV attachments.

### Identify the Six Standard Reports

Map each CSV to its report type by inspecting the filename and/or the CSV
header row. See [csv-column-reference.md](./references/csv-column-reference.md)
for the exact column names per report.

| # | Report Type        | Expected Filename Pattern             |
|---|--------------------|---------------------------------------|
| 1 | Traffic Overview   | `*traffic_overview*` / `*sessions*`   |
| 2 | Channel Grouping   | `*channel*` / `*acquisition*`         |
| 3 | Landing Pages      | `*landing*` / `*page_path*`           |
| 4 | Search Queries     | `*query*` / `*search*`                |
| 5 | Device Breakdown   | `*device*` / `*category*`             |
| 6 | Page Engagement    | `*engagement*` / `*avg_time*`         |

> **Fallback**: If fewer than six CSVs are found, proceed in "General Movement"
> mode using whatever CSVs are available. Adjust the report sections
> accordingly and note which data is missing.

---

## Step 2 — Set Up the Dated Folder

Determine the Monday date of this reporting week (ISO format: `YYYY-MM-DD`).

```
~/analytics-reports/
└── YYYY-MM-DD/
    ├── raw/          <- save the original CSV files here
    └── report/       <- save the finished HTML report here
```

Create the folder structure. Copy each CSV into `raw/` with its original
filename.

---

## Step 3 — Load Last Week's Data for Comparison

Find the **most recent dated folder** before this week inside
`~/analytics-reports/`. Load the corresponding CSVs from its `raw/` directory.

If no previous week exists, skip all week-over-week comparisons and note "First
week — no comparison available" in the report.

---

## Step 4 — Parse and Analyse the Data

For each CSV pair (this week vs last week), compute the following. See
[metrics-reference.md](./references/metrics-reference.md) for the full formula
definitions.

### Traffic Overview
- Total sessions (this week vs last week, % change)
- Total users / new users
- Bounce rate / engagement rate
- Average session duration

### Channel Grouping
- Sessions by channel (Organic Search, Direct, Email, Social, Referral, Other)
- % change per channel vs last week
- Identify the channel with the largest absolute gain and largest absolute drop

### Landing Pages
- Top 10 pages by sessions (new vs returning)
- Top 3 pages by new users
- Pages with the largest session increase / decrease vs last week

### Search Queries
- Top 20 queries by clicks
- Queries with growing impressions (week-over-week)
- Average position for top 10 queries
- Total clicks + total impressions (% change)

### Device Breakdown
- Sessions split across Desktop / Mobile / Tablet (% share)
- Week-over-week shift in mobile share

### Page Engagement
- Top 10 pages by average engagement time
- Pages above and below the site average
- Any page where engagement time improved or dropped significantly (>20%)

### Written Summary
Write a concise 3-5 paragraph narrative that answers:
1. Did total traffic rise or fall, and why (which channel explains it)?
2. Is search momentum improving (impressions, clicks, average position)?
3. Which content is performing well, and which content needs attention?
4. What is one specific thing the user could act on this week?

---

## Step 5 — Build the Visual HTML Artifact

Create a single self-contained HTML file. The report must include the sections
below. See [report-template.html](./resources/report-template.html) for the
base layout and colour palette.

### Report Structure

```
Header
  ├── Site name + reporting week date range
  └── Generated timestamp

Section 1 — Weekly Summary (written narrative)

Section 2 — Traffic at a Glance
  ├── KPI cards: Sessions, Users, New Users, Avg Session Duration, Bounce Rate
  └── Line chart: Sessions this week vs last week (day by day if available,
      otherwise a single grouped bar)

Section 3 — Traffic by Channel
  ├── Stacked bar chart: Sessions by channel, this week vs last week
  └── Table: Channel | This Week | Last Week | Change | % Change

Section 4 — Search Performance
  ├── KPI cards: Total Clicks, Total Impressions, CTR, Avg Position
  ├── Table: Top 20 queries (Query | Clicks | Impressions | CTR | Avg Position)
  └── Trend callout: Growing queries (impressions up >= 10% week-over-week)

Section 5 — Top Landing Pages
  ├── Table: Top 10 by sessions (Page | Sessions | New Users | Change | % Change)
  └── Callout: Pages with the largest gains and the largest drops

Section 6 — Device Split
  └── Donut chart: Desktop / Mobile / Tablet this week, with % labels

Section 7 — Page Engagement
  ├── Table: Top 10 by avg engagement time
  └── Callout: Pages improved / declined >= 20%

Footer
  └── Data source note + folder path where raw CSVs are saved
```

### Visual Requirements

- Dark background (`#0f1117`) with white text
- Accent colour: `#4f8ef7` (blue) for charts and highlights
- Positive changes displayed in green (`#22c55e`)
- Negative changes displayed in red (`#ef4444`)
- Charts built with **Chart.js** (loaded from CDN — no external data calls)
- Fully self-contained: no external fonts or images required; use system font
  stack
- Responsive layout (CSS Grid / Flexbox)

---

## Step 6 — Save the Finished Report

Write the HTML file to:

```
~/analytics-reports/YYYY-MM-DD/report/weekly-report-YYYY-MM-DD.html
```

Confirm the file was written. Print the full path to the user.

---

## Step 7 — Present the Artifact

Render the finished HTML as a Claude Artifact in the chat so the user can view
it immediately without opening the file. Then output a brief plain-text recap:

```
✅ Weekly Analytics Report — Week of YYYY-MM-DD

📁 Saved to: ~/analytics-reports/YYYY-MM-DD/
   ├── raw/   (6 CSV files)
   └── report/weekly-report-YYYY-MM-DD.html

📊 Quick Stats
   Sessions:    X,XXX  (up/down X.X% vs last week)
   Organic:     X,XXX  (up/down X.X%)
   Top Query:   "..."  (X clicks)
   Top Page:    /...   (X sessions)

📝 Key Insight: [One sentence from the written summary]
```

---

## Error Handling

| Situation | Action |
|-----------|--------|
| Gmail access unavailable | Ask user to paste CSV content or attach files directly in the chat. |
| Fewer than 6 CSVs found | Run in "General Movement" mode; note missing reports. |
| No previous week data | Skip comparisons; label all metrics as "No prior data". |
| CSV parsing error | Log the error, skip that report section, and note it in the Artifact. |
| Data directory unwritable | Warn the user; still create the Artifact in chat. |

---

## References

- [report-setup-guide.md](./references/report-setup-guide.md) — How to create
  and schedule the six GA4 reports in Google Analytics.
- [csv-column-reference.md](./references/csv-column-reference.md) — Exact
  column names for each CSV report type.
- [metrics-reference.md](./references/metrics-reference.md) — Formula
  definitions for all calculated metrics.
- [report-template.html](./resources/report-template.html) — Base HTML/CSS
  template for the Artifact.
