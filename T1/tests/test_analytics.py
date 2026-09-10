"""test_analytics.py — Tests for the analytics calculation layer."""
import pytest
from validate import validate_files
from parse import parse_reports, ParsedReports
from analytics import calculate, _pct_change, _weighted_avg, _fmt_duration


class TestUtilityFunctions:
    def test_pct_change_positive(self):
        assert _pct_change(110, 100) == pytest.approx(10.0)

    def test_pct_change_negative(self):
        assert _pct_change(90, 100) == pytest.approx(-10.0)

    def test_pct_change_zero_denominator_returns_none(self):
        assert _pct_change(50, 0) is None

    def test_pct_change_zero_numerator(self):
        assert _pct_change(0, 100) == pytest.approx(-100.0)

    def test_pct_change_both_zero(self):
        assert _pct_change(0, 0) is None

    def test_weighted_avg_equal_weights(self):
        assert _weighted_avg([3.0, 5.0], [1.0, 1.0]) == pytest.approx(4.0)

    def test_weighted_avg_different_weights(self):
        assert _weighted_avg([2.0, 4.0], [3.0, 1.0]) == pytest.approx(2.5)

    def test_weighted_avg_zero_total_weight(self):
        assert _weighted_avg([10.0, 20.0], [0.0, 0.0]) == 0.0

    def test_fmt_duration_whole_minutes(self):
        assert _fmt_duration(120) == "2:00"

    def test_fmt_duration_with_seconds(self):
        assert _fmt_duration(142) == "2:22"

    def test_fmt_duration_sub_minute(self):
        assert _fmt_duration(45) == "0:45"


class TestAnalyticsWithSampleData:
    @pytest.fixture
    def result_with_comparison(self, current_week_csvs, previous_week_csvs):
        cur_val = validate_files(current_week_csvs)
        prev_val = validate_files(previous_week_csvs)
        cur = parse_reports(cur_val.validated)
        prev = parse_reports(prev_val.validated)
        return calculate(cur, prev, "2026-08-31")

    @pytest.fixture
    def result_first_run(self, current_week_csvs):
        val = validate_files(current_week_csvs)
        cur = parse_reports(val.validated)
        return calculate(cur, None, None)

    def test_sessions_are_positive(self, result_with_comparison):
        assert result_with_comparison.sessions.value > 0

    def test_has_prior_data_flag(self, result_with_comparison, result_first_run):
        assert result_with_comparison.has_prior_data is True
        assert result_first_run.has_prior_data is False

    def test_first_run_pct_change_is_none(self, result_first_run):
        assert result_first_run.sessions.pct_change is None
        assert result_first_run.sessions.change_formatted == "N/A"

    def test_comparison_pct_change_is_numeric(self, result_with_comparison):
        # Current week is bigger than previous, so pct_change should be positive
        assert result_with_comparison.sessions.pct_change is not None
        assert isinstance(result_with_comparison.sessions.pct_change, float)

    def test_bounce_rate_direction_correct(self, result_with_comparison):
        # Lower bounce rate = better = direction should be "up"
        br = result_with_comparison.bounce_rate
        if br.pct_change is not None:
            if br.pct_change < 0:
                assert br.direction == "up"
            else:
                assert br.direction == "down"

    def test_channels_sorted_by_sessions_desc(self, result_with_comparison):
        sessions = [ch.sessions_tw for ch in result_with_comparison.channels]
        assert sessions == sorted(sessions, reverse=True)

    def test_avg_position_lower_is_better(self, result_with_comparison):
        pos = result_with_comparison.avg_position
        assert pos.lower_is_better is True

    def test_top_queries_capped_at_20(self, result_with_comparison):
        assert len(result_with_comparison.top_queries) <= 20

    def test_device_shares_sum_to_100(self, result_with_comparison):
        total = sum(d.share_pct for d in result_with_comparison.devices)
        assert total == pytest.approx(100.0, abs=1.0)   # allow rounding tolerance

    def test_growing_queries_meet_threshold(self, result_with_comparison):
        for q in result_with_comparison.growing_queries:
            assert q.impression_pct_change is not None
            assert q.impression_pct_change >= 10.0

    def test_top_engaged_pages_sorted_desc(self, result_with_comparison):
        times = [p.avg_engagement_time for p in result_with_comparison.top_engaged_pages]
        assert times == sorted(times, reverse=True)

    def test_total_clicks_zero_on_empty_search(self):
        """If no search data, clicks/impressions should be 0 safely."""
        empty = ParsedReports()
        result = calculate(empty, None, None)
        assert result.total_clicks.value == 0.0
        assert result.avg_position.value == 0.0

    def test_no_crash_on_all_empty_parsed_reports(self):
        """Full calculation with all-empty ParsedReports should not raise."""
        empty = ParsedReports()
        result = calculate(empty, None, None)
        assert result.has_prior_data is False
        assert result.sessions.value == 0.0
