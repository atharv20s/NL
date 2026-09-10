"""test_parse.py — Tests for the CSV parsing layer."""
import pytest
from validate import validate_files
from parse import parse_reports, _to_float


class TestToFloat:
    """Test the _to_float helper directly."""
    def test_plain_number(self):      assert _to_float("1234", "sessions", 0) == 1234.0
    def test_comma_thousands(self):   assert _to_float("1,234", "sessions", 0) == 1234.0
    def test_percentage_as_decimal(self): assert _to_float("45%", "bounce_rate", 0) == pytest.approx(0.45)
    def test_already_decimal_rate(self): assert _to_float("0.45", "bounce_rate", 0) == pytest.approx(0.45)
    def test_rate_over_1_normalised(self): assert _to_float("45", "bounce_rate", 0) == pytest.approx(0.45)
    def test_empty_string(self):      assert _to_float("", "sessions", 0) == 0.0
    def test_dash(self):              assert _to_float("-", "sessions", 0) == 0.0
    def test_na(self):                assert _to_float("N/A", "sessions", 0) == 0.0
    def test_not_set(self):           assert _to_float("(not set)", "sessions", 0) == 0.0
    def test_float_string(self):      assert _to_float("3.14", "avg_position", 0) == pytest.approx(3.14)


class TestParseSampleData:
    def test_parse_all_six_reports(self, current_week_csvs):
        validation = validate_files(current_week_csvs)
        assert validation.success
        parsed = parse_reports(validation.validated)

        assert len(parsed.traffic_overview) == 7       # 7 days
        assert len(parsed.channel_grouping) == 7       # 7 channels
        assert len(parsed.landing_pages) == 10
        assert len(parsed.search_queries) == 20
        assert len(parsed.device_breakdown) == 3
        assert len(parsed.page_engagement) == 12

    def test_traffic_values_are_numeric(self, current_week_csvs):
        validation = validate_files(current_week_csvs)
        parsed = parse_reports(validation.validated)
        for row in parsed.traffic_overview:
            assert isinstance(row.sessions, float)
            assert row.sessions >= 0
            assert 0.0 <= row.bounce_rate <= 1.0
            assert row.avg_session_duration >= 0

    def test_search_ctr_in_range(self, current_week_csvs):
        validation = validate_files(current_week_csvs)
        parsed = parse_reports(validation.validated)
        for q in parsed.search_queries:
            assert 0.0 <= q.ctr <= 1.0, f"CTR out of range for query: {q.query}"

    def test_device_categories_are_strings(self, current_week_csvs):
        validation = validate_files(current_week_csvs)
        parsed = parse_reports(validation.validated)
        for d in parsed.device_breakdown:
            assert isinstance(d.device_category, str)
            assert len(d.device_category) > 0

    def test_malformed_row_does_not_crash(self, tmp_csv):
        """A row with fewer columns than the header should parse with zeros."""
        path = tmp_csv("traffic_overview.csv", (
            "Date,Sessions,Active Users,New Users,Bounce Rate,Engagement Rate,Average Session Duration\n"
            "20260901,312\n"   # truncated row
            "20260902,278,259,181,0.40,0.60,128\n"
        ))
        validation = validate_files([path])
        parsed = parse_reports(validation.validated)
        assert len(parsed.traffic_overview) == 2
        # First row: sessions=312, rest=0
        assert parsed.traffic_overview[0].sessions == 312.0
        assert parsed.traffic_overview[0].new_users == 0.0
        # Second row: fully parsed
        assert parsed.traffic_overview[1].sessions == 278.0

    def test_comma_in_number_parsed_correctly(self, tmp_csv):
        path = tmp_csv("channel_grouping.csv", (
            "Session default channel group,Sessions,New Users,Bounce Rate,Engagement Rate,Active Users\n"
            "Organic Search,\"1,234\",890,0.35,0.65,1200\n"
        ))
        validation = validate_files([path])
        parsed = parse_reports(validation.validated)
        assert parsed.channel_grouping[0].sessions == 1234.0

    def test_no_data_rows_returns_empty_list(self, tmp_csv):
        path = tmp_csv("device_breakdown.csv", (
            "Device category,Sessions,Active Users,New Users,Bounce Rate\n"
        ))
        validation = validate_files([path])
        parsed = parse_reports(validation.validated)
        assert parsed.device_breakdown == []
        assert len(parsed.parse_warnings) == 0   # header-only is a validation warning, not a parse error
