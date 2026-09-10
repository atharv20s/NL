"""test_report_gen.py — Tests for the HTML report generator."""
import pytest
from validate import validate_files
from parse import parse_reports, ParsedReports
from analytics import calculate
from interpret import generate_interpretation
from report_gen import generate_report


@pytest.fixture
def full_result(current_week_csvs, previous_week_csvs):
    cur = parse_reports(validate_files(current_week_csvs).validated)
    prev = parse_reports(validate_files(previous_week_csvs).validated)
    return calculate(cur, prev, "2026-08-31")


@pytest.fixture
def first_run_result(current_week_csvs):
    cur = parse_reports(validate_files(current_week_csvs).validated)
    return calculate(cur, None, None)


class TestGenerateReport:
    def test_returns_html_string(self, full_result):
        interp = generate_interpretation(full_result)
        html = generate_report(full_result, interp, "2026-09-08",
                               "C:/Users/athar/analytics-reports")
        assert isinstance(html, str)
        assert len(html) > 1000

    def test_html_contains_doctype(self, full_result):
        interp = generate_interpretation(full_result)
        html = generate_report(full_result, interp, "2026-09-08",
                               "C:/Users/athar/analytics-reports")
        assert "<!DOCTYPE html>" in html

    def test_html_contains_week_date(self, full_result):
        interp = generate_interpretation(full_result)
        html = generate_report(full_result, interp, "2026-09-08",
                               "C:/Users/athar/analytics-reports")
        assert "2026-09-08" in html

    def test_html_contains_sessions_value(self, full_result):
        interp = generate_interpretation(full_result)
        html = generate_report(full_result, interp, "2026-09-08",
                               "C:/Users/athar/analytics-reports")
        # The sessions KPI value (e.g. "1,886") should appear somewhere in the report
        assert full_result.sessions.formatted in html or str(int(full_result.sessions.value)) in html

    def test_first_run_banner_present(self, first_run_result):
        interp = generate_interpretation(first_run_result)
        html = generate_report(first_run_result, interp, "2026-09-08",
                               "C:/Users/athar/analytics-reports")
        assert "First run detected" in html

    def test_no_first_run_banner_when_prior_data(self, full_result):
        interp = generate_interpretation(full_result)
        html = generate_report(full_result, interp, "2026-09-08",
                               "C:/Users/athar/analytics-reports")
        assert "First run detected" not in html

    def test_chart_js_script_included(self, full_result):
        interp = generate_interpretation(full_result)
        html = generate_report(full_result, interp, "2026-09-08",
                               "C:/Users/athar/analytics-reports")
        assert "chart.js" in html.lower()

    def test_report_with_empty_parsed_reports_does_not_crash(self):
        empty = ParsedReports()
        result = calculate(empty, None, None)
        interp = generate_interpretation(result)
        html = generate_report(result, interp, "2026-09-08",
                               "C:/Users/athar/analytics-reports")
        assert "<!DOCTYPE html>" in html
        assert "No data" in html or "no data" in html.lower() or "No" in html

    def test_action_item_appears_in_report(self, full_result):
        interp = generate_interpretation(full_result)
        html = generate_report(full_result, interp, "2026-09-08",
                               "C:/Users/athar/analytics-reports")
        # At least part of the action item should appear
        assert "Action item" in html or "action" in html.lower()
