"""PyQt6 Excel Export Dialog for Work Buddy."""

from __future__ import annotations

import calendar
import logging
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .excel_export import ExcelExporter
from .timer_engine import TimerEngine

logger = logging.getLogger("workbuddy")


class ExportDialogQt(QDialog):
    """Modern month-picker dialog for exporting Excel workbooks."""

    def __init__(
        self,
        parent: QWidget | None,
        engine: TimerEngine,
        months: list[tuple[int, int]],
    ) -> None:
        super().__init__(parent)
        self.engine = engine
        self.months = months
        self.setWindowTitle("Export to Excel")
        self.setFixedSize(320, 210)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setStyleSheet("""
            QDialog {
                background-color: #F8FAFC;
                font-family: 'Segoe UI', sans-serif;
            }
            QLabel {
                color: #1E293B;
            }
            QComboBox {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 8px;
                padding: 6px 12px;
                font-size: 13px;
                color: #0F172A;
            }
            QComboBox::drop-down {
                border: none;
            }
            QPushButton.primary {
                background-color: #2563EB;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton.primary:hover {
                background-color: #1D4ED8;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        lbl = QLabel("Select month to export:")
        lbl.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        layout.addWidget(lbl)

        self.combo = QComboBox()
        for y, m in self.months:
            self.combo.addItem(f"{calendar.month_name[m]} {y}")
        if self.months:
            self.combo.setCurrentIndex(len(self.months) - 1)
        layout.addWidget(self.combo)

        layout.addSpacing(10)

        btn_export = QPushButton("📊 Export Workbook")
        btn_export.setProperty("class", "primary")
        btn_export.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_export.clicked.connect(self._do_export)
        layout.addWidget(btn_export)

        layout.addStretch()

    def _do_export(self) -> None:
        idx = self.combo.currentIndex()
        if idx < 0:
            return
        year, month = self.months[idx]
        filename = f"{calendar.month_name[month]} {year}.xlsx"

        output, _ = QFileDialog.getSaveFileName(
            self,
            "Save Excel Report",
            str(Path.home() / "Documents" / filename),
            "Excel Files (*.xlsx)",
        )
        if not output:
            return

        try:
            ExcelExporter().export_month(
                self.engine.worklog, year, month, Path(output)
            )
            QMessageBox.information(
                self,
                "Export Complete",
                f"Exported successfully to:\n{output}",
            )
            logger.info("Excel export completed: %s", output)
            self.accept()
        except PermissionError:
            QMessageBox.critical(
                self,
                "Export Error",
                "Cannot write to that file.\n\n"
                "If the file is open in Excel, please close it and try again.",
            )
        except Exception as exc:
            QMessageBox.critical(
                self, "Export Error", f"Export failed:\n{exc}"
            )
            logger.error("Excel export failed: %s", exc)
