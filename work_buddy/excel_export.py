"""Excel report generation for Work Buddy."""

from __future__ import annotations

import calendar
import logging
from datetime import date
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill

from .models import DayRecord, WorkLog

logger = logging.getLogger("workbuddy")

# Styles
_HEADER_FONT = Font(bold=True, size=11)
_HEADER_FILL = PatternFill(start_color="D6E4F0", end_color="D6E4F0", fill_type="solid")
_HEADER_ALIGN = Alignment(horizontal="center")
_TOTAL_FONT = Font(bold=True, size=11)
_HOURS_FMT = "0.00"


class ExcelExporter:
    """Generates monthly Excel workbooks from work-log data.

    The workbook contains:
    * **Monthly Summary** — one row per day with total hours + grand total.
    * **One sheet per day** — start/end/hours/activity for each session.
    """

    def export_month(
        self,
        worklog: WorkLog,
        year: int,
        month: int,
        output_path: Path,
    ) -> None:
        """Create and save a workbook for the given month."""
        wb = Workbook()
        wb.remove(wb.active)  # remove the default blank sheet

        # Collect days with data
        days_with_data: list[tuple[date, DayRecord]] = []
        for date_str, day in sorted(worklog.days.items()):
            try:
                d = date.fromisoformat(date_str)
            except ValueError:
                continue
            if d.year == year and d.month == month and day.sessions:
                days_with_data.append((d, day))

        # Build sheets
        self._create_monthly_summary(wb, year, month, days_with_data)
        for d, day in days_with_data:
            self._create_daily_sheet(wb, d, day)

        wb.save(output_path)
        logger.info("Exported %d days to %s", len(days_with_data), output_path)

    # ------------------------------------------------------------------
    # Monthly Summary
    # ------------------------------------------------------------------

    def _create_monthly_summary(
        self,
        wb: Workbook,
        year: int,
        month: int,
        days_with_data: list[tuple[date, DayRecord]],
    ) -> None:
        title = "Monthly Summary"
        ws = wb.create_sheet(title, 0)
        ws.append(["Date", "Total Hours", "Sessions"])
        self._style_header(ws)

        grand_total = 0.0
        for d, day in days_with_data:
            hours = round(day.total_seconds() / 3600, 2)
            ws.append([d.strftime("%Y-%m-%d"), hours, len(day.sessions)])
            grand_total += hours

        # Grand total
        ws.append(["Total", round(grand_total, 2), ""])
        total_row = ws.max_row
        for col in (1, 2):
            ws.cell(total_row, col).font = _TOTAL_FONT

        # Number format for hours
        for row in range(2, total_row + 1):
            ws.cell(row, 2).number_format = _HOURS_FMT

        ws.column_dimensions["A"].width = 16
        ws.column_dimensions["B"].width = 14
        ws.column_dimensions["C"].width = 10
        ws.freeze_panes = "A2"

    # ------------------------------------------------------------------
    # Daily sheet
    # ------------------------------------------------------------------

    def _create_daily_sheet(
        self, wb: Workbook, d: date, day: DayRecord
    ) -> None:
        ws = wb.create_sheet(d.isoformat())
        ws.append(["Start Time", "End Time", "Hours Spent", "Project / Activity"])
        self._style_header(ws)

        total_hours = 0.0
        for s in day.sessions:
            start_str = s.start.strftime("%I:%M %p")
            end_str = s.end.strftime("%I:%M %p") if s.end else "Active"
            hours = round((s.duration_seconds or 0) / 3600, 2)
            total_hours += hours
            ws.append([start_str, end_str, hours, s.activity or ""])

        # Total row
        ws.append(["", "Total", round(total_hours, 2), ""])
        total_row = ws.max_row
        for col in (2, 3):
            ws.cell(total_row, col).font = _TOTAL_FONT

        # Number format
        for row in range(2, total_row + 1):
            ws.cell(row, 3).number_format = _HOURS_FMT

        ws.column_dimensions["A"].width = 14
        ws.column_dimensions["B"].width = 14
        ws.column_dimensions["C"].width = 14
        ws.column_dimensions["D"].width = 26
        ws.freeze_panes = "A2"

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _style_header(ws) -> None:
        """Apply bold + fill + center to the first row."""
        for cell in ws[1]:
            cell.font = _HEADER_FONT
            cell.fill = _HEADER_FILL
            cell.alignment = _HEADER_ALIGN
