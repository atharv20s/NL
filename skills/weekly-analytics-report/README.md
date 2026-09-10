# Claude Skill: Automated Weekly Google Analytics Reports

Turn scheduled Google Analytics 4 and Google Search Console CSV emails into an interactive, self-contained **Artifact report** in Claude.

Based on the setup by [Wyndo](https://substack.com/@wyndo).

---

## 📁 Skill Package Contents

```text
skills/weekly-analytics-report/
├── README.md                         # This guide
├── SKILL.md                          # The core skill prompt & step-by-step instructions
├── references/
│   ├── report-setup-guide.md         # How to schedule the 6 GA4 reports in Google Analytics
│   ├── csv-column-reference.md       # Exact column signatures & dimensions for each CSV
│   └── metrics-reference.md          # Formula definitions (WoW changes, CTR, position, shares)
└── resources/
    └── report-template.html          # Self-contained dark-mode dashboard template (Chart.js)
```

---

## 🚀 How to Use on Claude Web (claude.ai)

### Step 1: Create a Claude Project
1. Log in to [claude.ai](https://claude.ai) and click **Projects** in the sidebar.
2. Click **New Project** and name it `Weekly Analytics Report`.

### Step 2: Configure Project Knowledge & Instructions
1. Under **Project Instructions**, paste the contents of [`SKILL.md`](./SKILL.md).
2. Under **Project Knowledge**, upload:
   - `resources/report-template.html`
   - `references/csv-column-reference.md`
   - `references/metrics-reference.md`

### Step 3: Run Every Monday
1. Download the 6 CSV attachments from your Monday Google Analytics email.
2. Drag and drop the 6 CSVs into a new chat within the Project.
3. Type:
   ```text
   /weekly-analytics-report
   ```
4. Claude reads the CSV files, calculates week-over-week deltas, and renders the visual report inside an interactive **HTML Artifact**.

---

## 💻 How to Use in Claude Code CLI

Copy this entire folder into your Claude skills directory:
```bash
# Project-level:
cp -r skills/weekly-analytics-report .claude/skills/

# Global-level:
cp -r skills/weekly-analytics-report ~/.claude/skills/
```

Then in your terminal run:
```bash
claude
# Inside Claude Code:
/weekly-analytics-report
```
