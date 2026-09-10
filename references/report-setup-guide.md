# Google Analytics Report Setup Guide

This guide explains how to create and schedule the six CSV reports inside
Google Analytics that the `/weekly-analytics-report` skill depends on.

---

## Overview

All six reports are created inside **Google Analytics 4** (not Search Console).
Because you link Search Console to your GA4 property, the search query data is
available from within GA4's reporting interface — so everything is scheduled
from one place.

Reports are emailed automatically every Monday at a time you choose. The skill
searches your inbox for those emails and reads the CSV attachments.

---

## Before You Start

1. Log in to [analytics.google.com](https://analytics.google.com).
2. Select the correct GA4 property for your site.
3. Confirm that Google Search Console is linked:
   - Go to **Admin → Property → Search Console Links** and verify your site
     appears.

---

## Report 1 — Traffic Overview

**Purpose**: Top-level view of sessions, users, and engagement for the week.

| Setting | Value |
|---------|-------|
| Report type | Standard report → Acquisition → Overview |
| Date range | Last 7 days (set as default) |
| Metrics | Sessions, Active Users, New Users, Bounce Rate, Average Session Duration |
| Dimensions | Date |
| Export format | CSV |
| Schedule | Every Monday at 07:00 (your local time) |
| Filename prefix | `traffic_overview` |

**Steps**:
1. In GA4, go to **Reports → Acquisition → Overview**.
2. Set the date range to "Last 7 days".
3. Click **Share this report** → **Schedule email**.
4. Choose CSV, set frequency to Weekly, day = Monday, and enter your email.

---

## Report 2 — Channel Grouping

**Purpose**: Shows which marketing channels (Organic, Direct, Email, Social,
etc.) are driving sessions.

| Setting | Value |
|---------|-------|
| Report type | Standard report → Acquisition → Traffic Acquisition |
| Date range | Last 7 days |
| Primary dimension | Session default channel group |
| Metrics | Sessions, New Users, Bounce Rate, Engagement Rate |
| Export format | CSV |
| Schedule | Every Monday at 07:00 |
| Filename prefix | `channel_grouping` |

---

## Report 3 — Landing Pages

**Purpose**: Shows which pages people land on first — the "front doors" of
your site.

| Setting | Value |
|---------|-------|
| Report type | Standard report → Engagement → Landing Page |
| Date range | Last 7 days |
| Primary dimension | Landing page + query string |
| Metrics | Sessions, New Users, Bounce Rate, Average Session Duration |
| Sort | Sessions descending |
| Rows | Top 50 |
| Export format | CSV |
| Schedule | Every Monday at 07:00 |
| Filename prefix | `landing_pages` |

---

## Report 4 — Search Queries

**Purpose**: Shows what people typed into Google before clicking through to
your site. Requires the Search Console link.

| Setting | Value |
|---------|-------|
| Report type | Standard report → Acquisition → Search Console → Queries |
| Date range | Last 7 days |
| Metrics | Clicks, Impressions, CTR, Average Position |
| Sort | Clicks descending |
| Rows | Top 100 |
| Export format | CSV |
| Schedule | Every Monday at 07:00 |
| Filename prefix | `search_queries` |

> **Note**: Search Console data in GA4 has a 2–3 day delay. Monday's report
> will cover approximately last Monday through last Friday.

---

## Report 5 — Device Breakdown

**Purpose**: Shows the split between Desktop, Mobile, and Tablet users.

| Setting | Value |
|---------|-------|
| Report type | Standard report → User → Tech → Overview, filtered by Device Category |
| Date range | Last 7 days |
| Primary dimension | Device category |
| Metrics | Sessions, Active Users, Bounce Rate |
| Export format | CSV |
| Schedule | Every Monday at 07:00 |
| Filename prefix | `device_breakdown` |

---

## Report 6 — Page Engagement

**Purpose**: Shows how long people spend on your pages — a proxy for content
quality.

| Setting | Value |
|---------|-------|
| Report type | Standard report → Engagement → Pages and Screens |
| Date range | Last 7 days |
| Primary dimension | Page path + screen class |
| Metrics | Views, Active Users, Average Engagement Time, Engagement Rate |
| Sort | Average Engagement Time descending |
| Rows | Top 50 |
| Export format | CSV |
| Schedule | Every Monday at 07:00 |
| Filename prefix | `page_engagement` |

---

## Verifying the Schedule

After setting up all six schedules:

1. Check **Admin → Scheduled Emails** in GA4 to see all active schedules.
2. Wait for the first Monday delivery, then confirm all six CSV emails arrive.
3. Run `/weekly-analytics-report` and let the skill locate the emails.

---

## Adjusting for Different Business Types

The six reports above are optimised for content, newsletter, and audience-
building sites. If your business measures different outcomes, replace or add
reports:

| Business Type | Suggested Substitution |
|---------------|------------------------|
| Coaching / Services | Replace Device Breakdown with a Goals / Conversions report |
| E-commerce | Replace Page Engagement with a Product Performance report |
| SaaS / App | Replace Landing Pages with an Events / Feature Usage report |
| Local Business | Add a Geographic Breakdown report |

The skill will adapt automatically — it inspects the CSV headers before
deciding which sections to generate.
