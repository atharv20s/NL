"""test_compare.py — Tests for historical comparison (previous-run discovery)."""
import pytest
import shutil
from datetime import date
from pathlib import Path

from compare import find_previous_run, _is_valid_dated_dir, _parse_date


class TestHelpers:
    def test_parse_date_valid(self):
        d = _parse_date("2026-09-07")
        assert d == date(2026, 9, 7)

    def test_parse_date_invalid(self):
        assert _parse_date("not-a-date") is None
        assert _parse_date("20260907") is None   # wrong format

    def test_is_valid_dated_dir_true(self, tmp_path):
        run_dir = tmp_path / "2026-09-01"
        raw_dir = run_dir / "raw"
        raw_dir.mkdir(parents=True)
        (raw_dir / "traffic_overview.csv").write_text("a,b\n1,2\n")
        assert _is_valid_dated_dir(run_dir) is True

    def test_is_valid_dated_dir_no_csv(self, tmp_path):
        run_dir = tmp_path / "2026-09-01"
        (run_dir / "raw").mkdir(parents=True)
        # No CSVs in raw/
        assert _is_valid_dated_dir(run_dir) is False

    def test_is_valid_dated_dir_wrong_name(self, tmp_path):
        run_dir = tmp_path / "not-a-date"
        (run_dir / "raw").mkdir(parents=True)
        assert _is_valid_dated_dir(run_dir) is False

    def test_is_valid_dated_dir_is_file(self, tmp_path):
        f = tmp_path / "2026-09-01"
        f.write_text("x")
        assert _is_valid_dated_dir(f) is False


class TestFindPreviousRun:
    def _make_run(self, root: Path, date_str: str, csv_content: str):
        """Create a minimal valid dated run directory."""
        raw = root / date_str / "raw"
        raw.mkdir(parents=True, exist_ok=True)
        # Copy sample search_queries.csv as a minimal valid CSV
        (raw / "search_queries.csv").write_text(csv_content)

    VALID_CSV = (
        "Query,Clicks,Impressions,CTR,Average Position\n"
        "ai tools,100,1200,0.08,4.5\n"
    )

    def test_no_data_root_returns_none(self, tmp_path):
        result = find_previous_run(tmp_path / "nonexistent", date(2026, 9, 8))
        assert result is None

    def test_first_run_returns_none(self, tmp_path):
        # Data root exists but no dated directories
        result = find_previous_run(tmp_path, date(2026, 9, 8))
        assert result is None

    def test_finds_most_recent_previous(self, tmp_path):
        self._make_run(tmp_path, "2026-08-25", self.VALID_CSV)
        self._make_run(tmp_path, "2026-09-01", self.VALID_CSV)
        # Current run date: 2026-09-08
        result = find_previous_run(tmp_path, date(2026, 9, 8))
        assert result is not None
        assert result.date_str == "2026-09-01"   # closest before 2026-09-08

    def test_does_not_use_same_date(self, tmp_path):
        self._make_run(tmp_path, "2026-09-08", self.VALID_CSV)
        result = find_previous_run(tmp_path, date(2026, 9, 8))
        assert result is None   # same date excluded

    def test_does_not_use_future_date(self, tmp_path):
        self._make_run(tmp_path, "2026-09-10", self.VALID_CSV)
        result = find_previous_run(tmp_path, date(2026, 9, 8))
        assert result is None

    def test_does_not_assume_7_day_gap(self, tmp_path):
        """Previous run is 3 days ago, not 7. Should still be found."""
        self._make_run(tmp_path, "2026-09-05", self.VALID_CSV)
        result = find_previous_run(tmp_path, date(2026, 9, 8))
        assert result is not None
        assert result.date_str == "2026-09-05"

    def test_skips_invalid_directories(self, tmp_path):
        self._make_run(tmp_path, "2026-09-01", self.VALID_CSV)
        # Create a non-date directory
        (tmp_path / "random-folder").mkdir()
        # Create a dated dir but no CSVs
        (tmp_path / "2026-09-05" / "raw").mkdir(parents=True)

        result = find_previous_run(tmp_path, date(2026, 9, 8))
        assert result is not None
        assert result.date_str == "2026-09-01"


class TestIdempotency:
    """Running the pipeline twice with the same date should not conflict."""

    def test_setup_run_directory_idempotent(self, tmp_path):
        from persist import setup_run_directory
        raw1, report1 = setup_run_directory(tmp_path, "2026-09-08")
        raw2, report2 = setup_run_directory(tmp_path, "2026-09-08")
        assert raw1 == raw2
        assert report1 == report2
        assert raw1.exists()

    def test_save_raw_csvs_overwrites(self, tmp_path, tmp_csv):
        from persist import setup_run_directory, save_raw_csvs
        csv_path = tmp_csv("traffic_overview.csv", "Date,Sessions\n20260901,312\n")
        raw_dir, _ = setup_run_directory(tmp_path, "2026-09-08")

        saved1 = save_raw_csvs([csv_path], raw_dir)
        saved2 = save_raw_csvs([csv_path], raw_dir)

        # Same file, no duplicates
        assert len(list(raw_dir.glob("*.csv"))) == 1
        assert saved1 == saved2
