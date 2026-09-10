"""test_validate.py — Tests for the validation layer."""
import pytest
from validate import (
    validate_files, ReportType, ValidationResult,
    identify_report_type,
)


class TestIdentifyReportType:
    def test_traffic_overview_identified(self, tmp_csv):
        path = tmp_csv("traffic_overview.csv", (
            "# header\n"
            "Date,Sessions,Active Users,New Users,Bounce Rate,Engagement Rate,Average Session Duration\n"
            "20260901,312,289,201,0.38,0.62,142\n"
        ))
        rtype, header_idx, cols, row_count = identify_report_type(path, "traffic_overview.csv")
        assert rtype == ReportType.TRAFFIC_OVERVIEW
        assert "sessions" in cols
        assert row_count == 1

    def test_channel_grouping_identified(self, tmp_csv):
        path = tmp_csv("channel_grouping.csv", (
            "Session default channel group,Sessions,New Users\n"
            "Organic Search,891,634\n"
        ))
        rtype, _, cols, _ = identify_report_type(path, "channel_grouping.csv")
        assert rtype == ReportType.CHANNEL_GROUPING

    def test_search_queries_identified(self, tmp_csv):
        path = tmp_csv("search_queries.csv", (
            "Query,Clicks,Impressions,CTR,Average Position\n"
            "best ai tools,100,1200,0.08,4.5\n"
        ))
        rtype, _, _, _ = identify_report_type(path, "search_queries.csv")
        assert rtype == ReportType.SEARCH_QUERIES

    def test_device_breakdown_identified(self, tmp_csv):
        path = tmp_csv("device_breakdown.csv", (
            "Device category,Sessions,Active Users\n"
            "desktop,1000,950\n"
        ))
        rtype, _, _, _ = identify_report_type(path, "device_breakdown.csv")
        assert rtype == ReportType.DEVICE_BREAKDOWN

    def test_page_engagement_identified(self, tmp_csv):
        path = tmp_csv("page_engagement.csv", (
            "Page path + screen class,Views,Average Engagement Time\n"
            "/blog/post,400,212\n"
        ))
        rtype, _, _, _ = identify_report_type(path, "page_engagement.csv")
        assert rtype == ReportType.PAGE_ENGAGEMENT

    def test_landing_pages_identified(self, tmp_csv):
        path = tmp_csv("landing_pages.csv", (
            "Landing page + query string,Sessions,New Users\n"
            "/blog/my-post,200,150\n"
        ))
        rtype, _, _, _ = identify_report_type(path, "landing_pages.csv")
        assert rtype == ReportType.LANDING_PAGES

    def test_ga4_metadata_header_skipped(self, tmp_csv):
        """GA4 exports have 2-6 metadata rows before the real header."""
        path = tmp_csv("traffic_overview.csv", (
            "# Google Analytics Data Export\n"
            "# Start date: 2026-09-01\n"
            "# End date: 2026-09-07\n"
            "# Report: Traffic Overview\n"
            "\n"
            "Date,Sessions,Active Users,New Users,Bounce Rate,Average Session Duration\n"
            "20260901,312,289,201,0.38,142\n"
        ))
        rtype, header_idx, _, row_count = identify_report_type(path, "traffic_overview.csv")
        assert rtype == ReportType.TRAFFIC_OVERVIEW
        assert header_idx == 5   # row index of the real header
        assert row_count == 1

    def test_empty_file_raises(self, tmp_csv):
        path = tmp_csv("empty.csv", "")
        with pytest.raises(ValueError, match="empty"):
            identify_report_type(path, "empty.csv")

    def test_unknown_columns_returns_unknown(self, tmp_csv):
        """Non-GA4 columns should return UNKNOWN, not raise."""
        path = tmp_csv("mystery.csv", (
            "ProductID,SKU,Price\n"
            "1001,ABC,9.99\n"
        ))
        rtype, _, _, _ = identify_report_type(path, "mystery.csv")
        assert rtype == ReportType.UNKNOWN


class TestValidateFiles:
    def test_all_six_sample_csvs_pass(self, current_week_csvs):
        result = validate_files(current_week_csvs)
        assert result.success, f"Validation errors: {result.errors}"
        assert len(result.validated) == 6

    def test_nonexistent_file_is_error(self):
        result = validate_files(["/does/not/exist.csv"])
        assert not result.success
        assert any("does not exist" in str(e) for e in result.errors)

    def test_empty_file_is_error(self, tmp_csv):
        path = tmp_csv("empty.csv", "")
        result = validate_files([path])
        assert not result.success

    def test_missing_required_column_is_error(self, tmp_csv):
        # Search queries CSV without "impressions" column
        path = tmp_csv("search_queries.csv", (
            "Query,Clicks,CTR\n"
            "ai tools,50,0.05\n"
        ))
        result = validate_files([path])
        assert not result.success
        assert any("impressions" in str(e).lower() for e in result.errors)

    def test_duplicate_report_type_skips_second(self, tmp_csv):
        p1 = tmp_csv("search1.csv", (
            "Query,Clicks,Impressions,CTR,Average Position\n"
            "ai tools,100,1200,0.08,4.5\n"
        ))
        p2 = tmp_csv("search2.csv", (
            "Query,Clicks,Impressions,CTR,Average Position\n"
            "more tools,80,900,0.09,5.1\n"
        ))
        result = validate_files([p1, p2])
        types = [vr.report_type for vr in result.validated]
        assert types.count(ReportType.SEARCH_QUERIES) == 1

    def test_missing_report_types_reported(self, tmp_csv):
        # Only provide one report type
        path = tmp_csv("search_queries.csv", (
            "Query,Clicks,Impressions,CTR,Average Position\n"
            "ai tools,100,1200,0.08,4.5\n"
        ))
        result = validate_files([path])
        missing = result.missing_report_types()
        assert ReportType.TRAFFIC_OVERVIEW in missing
        assert ReportType.CHANNEL_GROUPING in missing
        assert ReportType.SEARCH_QUERIES not in missing
