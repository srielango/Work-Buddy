"""Tests for work_buddy.excel_export."""

import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path

from openpyxl import load_workbook

from work_buddy.excel_export import ExcelExporter
from work_buddy.models import DayRecord, Session, WorkLog


def _build_sample_worklog() -> WorkLog:
    """Create a worklog with two days of data in August 2026."""
    wl = WorkLog()

    # Aug 31
    day1 = wl.get_day(date(2026, 8, 31))
    day1.add_session(Session(
        start=datetime(2026, 8, 31, 9, 10),
        end=datetime(2026, 8, 31, 11, 40),
        duration_seconds=9000,
        activity="Trading Bot",
    ))
    day1.add_session(Session(
        start=datetime(2026, 8, 31, 12, 15),
        end=datetime(2026, 8, 31, 13, 45),
        duration_seconds=5400,
        activity="Python Learning",
    ))

    # Aug 30
    day2 = wl.get_day(date(2026, 8, 30))
    day2.add_session(Session(
        start=datetime(2026, 8, 30, 14, 0),
        end=datetime(2026, 8, 30, 17, 0),
        duration_seconds=10800,
        activity="Client Work",
    ))

    return wl


class TestExcelExport(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = Path(tempfile.mkdtemp())
        self.output_path = self.tmp_dir / "August 2026.xlsx"

    def tearDown(self):
        for f in self.tmp_dir.iterdir():
            f.unlink()
        self.tmp_dir.rmdir()

    def test_export_creates_file(self):
        wl = _build_sample_worklog()
        ExcelExporter().export_month(wl, 2026, 8, self.output_path)
        self.assertTrue(self.output_path.exists())

    def test_sheet_names(self):
        wl = _build_sample_worklog()
        ExcelExporter().export_month(wl, 2026, 8, self.output_path)
        wb = load_workbook(self.output_path)
        self.assertIn("Monthly Summary", wb.sheetnames)
        self.assertIn("2026-08-30", wb.sheetnames)
        self.assertIn("2026-08-31", wb.sheetnames)
        wb.close()

    def test_monthly_summary_content(self):
        wl = _build_sample_worklog()
        ExcelExporter().export_month(wl, 2026, 8, self.output_path)
        wb = load_workbook(self.output_path)
        ws = wb["Monthly Summary"]

        # Header
        self.assertEqual(ws.cell(1, 1).value, "Date")
        self.assertEqual(ws.cell(1, 2).value, "Total Hours")

        # Aug 30: 3 hours
        self.assertEqual(ws.cell(2, 1).value, "2026-08-30")
        self.assertAlmostEqual(ws.cell(2, 2).value, 3.0, places=2)

        # Aug 31: 2.5 + 1.5 = 4 hours
        self.assertEqual(ws.cell(3, 1).value, "2026-08-31")
        self.assertAlmostEqual(ws.cell(3, 2).value, 4.0, places=2)

        # Total row
        self.assertEqual(ws.cell(4, 1).value, "Total")
        self.assertAlmostEqual(ws.cell(4, 2).value, 7.0, places=2)

        wb.close()

    def test_daily_sheet_content(self):
        wl = _build_sample_worklog()
        ExcelExporter().export_month(wl, 2026, 8, self.output_path)
        wb = load_workbook(self.output_path)
        ws = wb["2026-08-31"]

        # Header
        self.assertEqual(ws.cell(1, 1).value, "Start Time")
        self.assertEqual(ws.cell(1, 4).value, "Project / Activity")

        # First session
        self.assertEqual(ws.cell(2, 4).value, "Trading Bot")
        self.assertAlmostEqual(ws.cell(2, 3).value, 2.5, places=2)

        # Second session
        self.assertEqual(ws.cell(3, 4).value, "Python Learning")
        self.assertAlmostEqual(ws.cell(3, 3).value, 1.5, places=2)

        # Total row
        self.assertEqual(ws.cell(4, 2).value, "Total")
        self.assertAlmostEqual(ws.cell(4, 3).value, 4.0, places=2)

        wb.close()

    def test_empty_month_creates_summary_only(self):
        wl = WorkLog()
        ExcelExporter().export_month(wl, 2026, 7, self.output_path)
        wb = load_workbook(self.output_path)
        self.assertEqual(wb.sheetnames, ["Monthly Summary"])
        wb.close()

    def test_no_activity_exported_as_empty_string(self):
        wl = WorkLog()
        day = wl.get_day(date(2026, 8, 15))
        day.add_session(Session(
            start=datetime(2026, 8, 15, 9, 0),
            end=datetime(2026, 8, 15, 10, 0),
            duration_seconds=3600,
        ))
        ExcelExporter().export_month(wl, 2026, 8, self.output_path)
        wb = load_workbook(self.output_path)
        ws = wb["2026-08-15"]
        self.assertIn(ws.cell(2, 4).value, ("", None))
        wb.close()

    def test_header_is_bold(self):
        wl = _build_sample_worklog()
        ExcelExporter().export_month(wl, 2026, 8, self.output_path)
        wb = load_workbook(self.output_path)
        ws = wb["Monthly Summary"]
        self.assertTrue(ws.cell(1, 1).font.bold)
        wb.close()

    def test_freeze_panes_set(self):
        wl = _build_sample_worklog()
        ExcelExporter().export_month(wl, 2026, 8, self.output_path)
        wb = load_workbook(self.output_path)
        ws = wb["Monthly Summary"]
        self.assertEqual(ws.freeze_panes, "A2")
        wb.close()


if __name__ == "__main__":
    unittest.main()
