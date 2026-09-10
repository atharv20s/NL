# We Collapsed 2 Hours of Weekly Google Analytics Admin into One Monday Artifact

> *"Whenever I'm stuck on whether to automate something, I ask one question: is this repetitive, or is this a decision? Repetitive gets automated. Decisions stay mine."*

A production-grade **Claude Skill** that turns scheduled Google Analytics 4 & Search Console CSV emails into an interactive, self-contained **HTML Artifact report**.

No Zapier. No n8n. No paid subscriptions. Just free scheduled emails, a Claude Skill, and an interactive dashboard that reveals what actually moved.

---

## 💡 The Result: What We Achieved

- **Before**: 45–90 minutes every Monday clicking through GA4 tabs, downloading separate spreadsheets, calculating week-over-week % changes by hand, and missing the real story (e.g., *traffic fell 11%, but high-intent search clicks grew +18%*).
- **After**: Drop 6 CSV email attachments into Claude, type `/weekly-analytics-report`, and get a complete, dark-mode visual Artifact dashboard with interactive Chart.js graphs, week-over-week deltas, and actionable insights in **under 30 seconds**.

---

## 🧠 The Philosophy: Repetitive vs. Decision

Most founders get trapped in one of two extremes:
1. **Ignoring analytics altogether** because opening 6 spreadsheets feels like starting an entire research project from scratch.
2. **Paying for bloated dashboard SaaS tools** ($50–$150/mo) that show 80 vanity metrics but don't explain *why* numbers shifted.

Here is the split:
- **Repetitive (Automated by Claude)**: Skipping GA4 metadata headers, matching columns, computing week-over-week percentage deltas, weighting search positions, ranking top landing pages, and generating charts.
- **Decision (Kept by Founder)**: Deciding what to write next, which underperforming landing page to rewrite, and which search query with breakout momentum (+10% impressions) to target.

---

## 🛠️ The 6 Core Reports

Instead of drowning in GA4's infinite menus, this setup tracks 5 essential questions:

| # | Report | The Question It Answers | Key Metrics Extracted |
|---|--------|-------------------------|------------------------|
| 1 | **Traffic Overview** | Did traffic change, and did the quality move with it? | Sessions, Users, Bounce Rate, Avg Duration |
| 2 | **Channel Grouping** | Which acquisition channel explains the movement? | Organic Search, Direct, Email, Social, Referral |
| 3 | **Landing Pages** | Which specific pages brought in new readers? | Page path, Sessions, New Users |
| 4 | **Search Queries** | What are people searching for, and what's gaining momentum? | Query, Clicks, Impressions, CTR, Position |
| 5 | **Device Breakdown** | Is the audience shifting between desktop and mobile? | Device Category, Sessions, % Share shift |
| 6 | **Page Engagement** | Are visitors actually reading, or bouncing immediately? | Page path, Average Engagement Time |

> **Graceful Degradation**: If Google Analytics only delivers 3 or 4 files, the skill automatically switches to *General Movement* mode rather than crashing.

---

## ⚠️ The "Quiet Failure" Gotchas We Solved

1. **The GA4 Metadata Trap**: GA4 scheduled CSVs don't start with headers on line 1. They often begin with `# Date Range: ...` and blank metadata lines. The skill scans down dynamically until it locates the actual column signatures.
2. **Zero-Division Crashes**: Week-over-week arithmetic crashes when prior week data is zero or missing. The skill enforces fallback defaults (`+100%` or `N/A`).
3. **The Average Position Distortion**: Plain averages of search rankings are misleading (a position 5 on a query with 2 impressions shouldn't outweigh position 8 on a query with 5,000 impressions). The skill calculates **weighted average position**: `sum(clicks × position) / sum(clicks)`.

---

## 🚀 How to Set This Up in Your Claude Web (Same-Day)

### Step 1: Add the Skill to Claude Web

1. Open [Claude.ai](https://claude.ai) and go to **Projects** > **New Project** (`Weekly Analytics`).
2. Click **Set Project Instructions** and paste the entire contents of [`SKILL.md`](./SKILL.md).
3. Under **Project Knowledge**, upload:
   - [`resources/report-template.html`](./resources/report-template.html) (HTML template)
   - [`references/csv-column-reference.md`](./references/csv-column-reference.md) (schema reference)
   - [`references/metrics-reference.md`](./references/metrics-reference.md) (formula reference)
4. Click **Save**.

### Step 2: Schedule the 6 GA4 Emails (One-Time Setup)

Follow our step-by-step checklist in [`references/report-setup-guide.md`](./references/report-setup-guide.md) to configure Google Analytics to email you the 6 CSV reports automatically every Monday morning.

### Step 3: Run Every Monday

1. Download the 6 CSV attachments from your Monday email.
2. Drag and drop them into your Claude Project chat.
3. Type:
   ```text
   /weekly-analytics-report
   ```
4. Claude reads the data, runs the calculations, and opens the interactive **HTML Artifact** dashboard directly on your screen.

---

## 📁 Repository Structure

```text
NL/
├── SKILL.md                          # The core Claude Skill instructions & prompt
├── README.md                         # This teardown and implementation guide
├── evals/
│   └── evals.json                    # Standardized evaluation test cases
├── references/
│   ├── report-setup-guide.md         # Exact clicks to schedule the 6 GA4 reports
│   ├── csv-column-reference.md       # Exact GA4/GSC column headers & dimensions
│   └── metrics-reference.md          # Pure mathematical formulas for all metrics
├── resources/
│   └── report-template.html          # Self-contained dark-mode dashboard template (Chart.js)
└── examples/
    ├── current_week/                 # 6 realistic sample CSVs for immediate testing
    ├── previous_week/                # 6 prior week CSVs for WoW comparison
    └── example-report.html           # Rendered example HTML Artifact dashboard
```

---

## 🧪 Testing with the Included Sample Data

You don't need to wait until Monday to verify that it works. Drag the 6 sample files from [`examples/current_week/`](./examples/current_week) into your Claude chat right now to preview your interactive dashboard.
