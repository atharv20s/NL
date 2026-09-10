# Metrics Reference

Defines every calculated metric used in the weekly analytics report, including
the formula, data sources, and interpretation guidance.

---

## General Conventions

- **This Week (TW)**: Data from the current Monday report.
- **Last Week (LW)**: Data from the previous Monday report (loaded from the
  dated folder).
- **% Change**: `((TW - LW) / LW) * 100`, rounded to one decimal place.
- **Absolute Change**: `TW - LW`.
- When `LW = 0`, % Change is displayed as "N/A (no prior data)".
- Positive % change is always considered favourable unless the metric is
  Bounce Rate or Average Position (lower is better for both).

---

## Traffic Overview Metrics

### Sessions
- **Formula**: Sum of the `Sessions` column across all rows in the Traffic
  Overview CSV.
- **Interpretation**: Total number of visits. A session ends after 30 minutes
  of inactivity (GA4 default).

### Active Users
- **Formula**: Sum of `Active Users` column.
- **Interpretation**: Users who triggered at least one engaged session.

### New Users
- **Formula**: Sum of `New Users` column.
- **Interpretation**: First-time visitors in the date range. A proxy for
  audience growth.

### Bounce Rate
- **Formula**: `Bounced Sessions / Total Sessions * 100`
- In GA4, the CSV exports `bounceRate` as a decimal. Multiply by 100 for
  display.
- **Interpretation**: Lower is better. A high bounce rate on a blog is not
  always bad — readers may read and leave. Compare with Average Engagement Time
  for context.

### Engagement Rate
- **Formula**: `1 - bounceRate` (GA4 definition). Or use the `engagementRate`
  column directly if present.
- **Interpretation**: Higher is better.

### Average Session Duration
- **Formula**: Mean of `Average Session Duration` values, weighted by Sessions
  per row if date-level data is available; otherwise use the single aggregated
  value.
- **Unit**: Seconds. Display as `m:ss` format (e.g., 2:34).
- **Interpretation**: Higher generally means more engaged visitors.

---

## Channel Grouping Metrics

### Sessions by Channel
- **Formula**: `Sessions` value for each `Session default channel group` row.
- **Week-over-Week Change**: Match channel names between TW and LW files.
  Channels present in TW but absent in LW are treated as LW = 0.

### Largest Absolute Gain
- The channel with the highest positive `Absolute Change` in sessions.

### Largest Absolute Drop
- The channel with the most negative `Absolute Change` in sessions.

### Channel Share %
- **Formula**: `Channel Sessions / Total Sessions * 100`
- Useful for spotting shifts in traffic mix even when total sessions change.

---

## Landing Page Metrics

### Sessions per Page
- The `Sessions` value for each `Landing page + query string` row.

### New User Rate
- **Formula**: `New Users / Sessions * 100`
- **Interpretation**: Pages with a high new user rate are effective at
  attracting first-time visitors — likely good SEO or referral targets.

### Page Gain / Drop
- Compare sessions per page between TW and LW. Rank by `Absolute Change`.
- Report top 3 gainers and top 3 droppers.

---

## Search Query Metrics

### Total Clicks
- **Formula**: Sum of `Clicks` across all query rows.

### Total Impressions
- **Formula**: Sum of `Impressions` across all query rows.

### Site-Level CTR
- **Formula**: `Total Clicks / Total Impressions * 100`
- **Interpretation**: Higher CTR means your titles and meta descriptions are
  compelling relative to competing search results.

### Average Position
- **Formula**: Weighted average: `Sum(Position_i * Impressions_i) / Sum(Impressions_i)`
- Do NOT use a simple mean — it under-weights low-traffic queries.
- **Interpretation**: Lower number = higher ranking. Improvement is a decrease.

### Growing Queries
- Queries where `Impressions(TW) / Impressions(LW) >= 1.10` (i.e., at least
  10% impression growth week-over-week).
- Used to surface topics gaining organic momentum.

---

## Device Breakdown Metrics

### Device Share %
- **Formula**: `Device Sessions / Total Sessions * 100`
- Computed for Desktop, Mobile, and Tablet separately.

### Mobile Share Shift
- **Formula**: `Mobile Share % (TW) - Mobile Share % (LW)`
- Positive = more mobile; negative = more desktop.

---

## Page Engagement Metrics

### Average Engagement Time per Page
- Use the `Average Engagement Time` column from the Page Engagement CSV.
- **Unit**: Seconds. Display as `m:ss`.

### Site Average Engagement Time
- **Formula**: Weighted mean across all pages:
  `Sum(EngagementTime_i * Views_i) / Sum(Views_i)`

### Significant Change Threshold
- A page is flagged as "significantly improved" or "significantly declined" if
  its `% Change in Average Engagement Time` is >= 20% or <= -20%.

---

## Written Summary Guidelines

The written summary should follow this structure:

**Paragraph 1 — Traffic Movement**
State total sessions (TW vs LW, % change). Name the one channel most
responsible for the change. Mention if quality signals (engagement rate,
session duration) moved with or against the traffic volume.

**Paragraph 2 — Search Momentum**
State total clicks and impressions (% change). Give the average position.
Mention 1–2 growing queries if they stand out.

**Paragraph 3 — Content Performance**
Name the top landing page and top engaged page. Mention any notable gainers or
droppers.

**Paragraph 4 — Action Item**
One concrete suggestion the user could act on this week, based directly on the
data. Examples:
- "Your /about page has grown 40% in sessions but has a 68% bounce rate —
  consider adding a clear call-to-action."
- "The query 'best email newsletter tools' is up 34% in impressions. You do not
  have a page targeting this term yet."
- "Mobile share grew from 41% to 51% this week — make sure your latest posts
  render well on small screens."
