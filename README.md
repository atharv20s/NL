# NL

Automated Weekly Google Analytics & Search Console Reports — Claude Skill and Automation Pipeline.

Based on the setup by [Wyndo](https://substack.com/@wyndo) (*"My Claude Skill for Automated Weekly Google Analytics Reports"*).

---

## 🎯 What This Repository Contains

This repository provides everything needed to turn scheduled weekly CSV reports from Google Analytics 4 and Google Search Console into an interactive, self-contained **HTML Artifact** report in Claude.

- 📦 **`skills/weekly-analytics-report/`**: The complete, standalone **Claude Skill** ready to use on **Claude Web ([claude.ai](https://claude.ai))**, Claude Projects, and Claude Code.
  - `SKILL.md`: Main Claude Skill prompt instructions (`/weekly-analytics-report`)
  - `references/report-setup-guide.md`: How to schedule the 6 GA4 reports to arrive in Gmail every Monday
  - `references/csv-column-reference.md`: Exact column headers and schemas for the 6 CSV files
  - `references/metrics-reference.md`: Exact formulas for week-over-week calculations, shares, and position weighting
  - `resources/report-template.html`: Self-contained dark-mode dashboard template with Chart.js charts
- ⚙️ **`T1/`**: The Python engine with deterministic analytics, Gmail OAuth2 ingestion, and 80/80 passing tests.
- 📊 **`T1/sample_data/`**: Realistic sample data (`current_week` & `previous_week`) for immediate offline testing.

---

## 🚀 How to Use on Claude Web (claude.ai)

1. **Create a Claude Project**:
   - Go to [claude.ai](https://claude.ai) > **Projects** > **New Project** (`Weekly Analytics Report`).
2. **Set Project Instructions**:
   - Copy the entire contents of [`skills/weekly-analytics-report/SKILL.md`](./skills/weekly-analytics-report/SKILL.md) and paste into **Project Instructions**.
3. **Add Project Knowledge**:
   - Upload `resources/report-template.html`, `references/csv-column-reference.md`, and `references/metrics-reference.md` into **Project Knowledge**.
4. **Run Every Monday**:
   - Download the 6 CSV attachments from your Monday email (or test with the sample CSVs in `T1/sample_data/current_week/`).
   - Drag & drop the 6 CSVs into the chat and type:
     ```text
     /weekly-analytics-report
     ```
   - Claude will render the full visual **HTML Artifact** dashboard directly in your browser.
