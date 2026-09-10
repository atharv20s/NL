# CSV Column Reference

This file lists the exact column (header) names the skill expects in each of
the six CSV reports exported from Google Analytics 4. Use these to identify
which report type a given CSV file corresponds to.

The skill matches columns case-insensitively and handles minor variations
(spaces vs underscores, camelCase vs snake_case). The "Primary Match" column
lists the most reliable identifier for each report type.

---

## Report 1 — Traffic Overview

**Primary Match**: file contains columns `Sessions` AND `Date`

| Column Name | GA4 API Name | Notes |
|-------------|--------------|-------|
| Date | `date` | Format: `YYYYMMDD` |
| Sessions | `sessions` | |
| Active Users | `activeUsers` | |
| New Users | `newUsers` | |
| Bounce Rate | `bounceRate` | Decimal (0–1) |
| Average Session Duration | `averageSessionDuration` | Seconds |
| Engagement Rate | `engagementRate` | Decimal (0–1) |

---

## Report 2 — Channel Grouping

**Primary Match**: file contains column `Session default channel group`

| Column Name | GA4 API Name | Notes |
|-------------|--------------|-------|
| Session default channel group | `sessionDefaultChannelGroup` | Organic Search, Direct, Email, etc. |
| Sessions | `sessions` | |
| New Users | `newUsers` | |
| Bounce Rate | `bounceRate` | |
| Engagement Rate | `engagementRate` | |
| Active Users | `activeUsers` | |

**Known channel values**:
- `Organic Search`
- `Direct`
- `Email`
- `Organic Social`
- `Referral`
- `Paid Search`
- `(Other)`
- `Unassigned`

---

## Report 3 — Landing Pages

**Primary Match**: file contains column `Landing page + query string`

| Column Name | GA4 API Name | Notes |
|-------------|--------------|-------|
| Landing page + query string | `landingPagePlusQueryString` | URL path, e.g. `/blog/post-title` |
| Sessions | `sessions` | |
| New Users | `newUsers` | |
| Bounce Rate | `bounceRate` | |
| Average Session Duration | `averageSessionDuration` | Seconds |
| Active Users | `activeUsers` | |

---

## Report 4 — Search Queries

**Primary Match**: file contains columns `Query` AND `Impressions`

| Column Name | GA4 API Name / SC Field | Notes |
|-------------|-------------------------|-------|
| Query | `searchQuery` | The search term |
| Clicks | `clicks` | From Search Console |
| Impressions | `impressions` | From Search Console |
| CTR | `ctr` | Click-through rate, decimal (0–1) |
| Average Position | `averagePosition` | Lower is better |

> **Note**: These columns come from the Search Console integration inside GA4.
> The CSV may also contain a `Date` column if exported with a date dimension.

---

## Report 5 — Device Breakdown

**Primary Match**: file contains column `Device category`

| Column Name | GA4 API Name | Notes |
|-------------|--------------|-------|
| Device category | `deviceCategory` | `desktop`, `mobile`, `tablet` |
| Sessions | `sessions` | |
| Active Users | `activeUsers` | |
| Bounce Rate | `bounceRate` | |
| New Users | `newUsers` | |

---

## Report 6 — Page Engagement

**Primary Match**: file contains column `Average engagement time`

| Column Name | GA4 API Name | Notes |
|-------------|--------------|-------|
| Page path + screen class | `pagePathPlusScreenClass` | URL path |
| Views | `screenPageViews` | |
| Active Users | `activeUsers` | |
| Average Engagement Time | `userEngagementDuration` / `averageSessionDuration` | Seconds |
| Engagement Rate | `engagementRate` | |

---

## Fallback / General Movement Mode

If no CSV matches the primary column signatures above, the skill enters
"General Movement" mode. In this mode it:

1. Reads all available CSVs.
2. Identifies numeric columns automatically.
3. Summarises totals and week-over-week changes for whatever data is present.
4. Notes in the report which standard sections are missing.

---

## Common Parsing Notes

- GA4 exports often include a **header block** (2–6 rows of metadata) before
  the actual column headers. The skill skips rows until it finds the true
  header row (detected by matching known column names).
- Numbers may be exported with commas as thousand separators — strip commas
  before parsing.
- Percentage columns (Bounce Rate, CTR, Engagement Rate) may be exported as
  decimals (0.45) or percentages (45%). Normalise to decimals for calculation.
- Date columns are `YYYYMMDD` format — parse with `strptime('%Y%m%d')`.
