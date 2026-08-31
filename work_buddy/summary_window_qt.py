"""PyQt6 Weekly Summary Window for Work Buddy."""

from __future__ import annotations

from datetime import date, timedelta

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QIcon
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from .models import format_duration
from .timer_engine import TimerEngine

_DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


class SummaryWindowQt(QDialog):
    """Modern modal dialog showing weekly daily breakdown and project totals."""

    def __init__(self, parent: QWidget | None, engine: TimerEngine) -> None:
        super().__init__(parent)
        self.engine = engine
        self.setWindowTitle("Weekly Summary — Work Buddy")
        self.setFixedSize(360, 520)
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
            QFrame.card {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 12px;
                padding: 12px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Title
        title = QLabel("📊 THIS WEEK")
        title.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        title.setStyleSheet("color: #0F172A;")
        layout.addWidget(title)

        # Daily Card
        daily_card = QFrame()
        daily_card.setProperty("class", "card")
        daily_layout = QVBoxLayout(daily_card)
        daily_layout.setSpacing(6)

        week = self.engine.week_summary()
        today = self.engine.clock().date()
        grand_total = 0

        for d, seconds in sorted(week.items()):
            is_today = (d == today)
            day_name = _DAY_NAMES[d.weekday()]
            dur = format_duration(seconds)

            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 2, 0, 2)

            lbl_day = QLabel(f"{day_name} ({d.strftime('%b %d')})")
            lbl_dur = QLabel(dur)

            if is_today:
                lbl_day.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
                lbl_dur.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
                lbl_day.setStyleSheet("color: #2563EB;")
                lbl_dur.setStyleSheet("color: #2563EB;")
            else:
                lbl_day.setFont(QFont("Segoe UI", 10))
                lbl_dur.setFont(QFont("Segoe UI", 10))
                lbl_day.setStyleSheet("color: #475569;")
                lbl_dur.setStyleSheet("color: #1E293B;")

            row_layout.addWidget(lbl_day)
            row_layout.addStretch()
            row_layout.addWidget(lbl_dur)
            daily_layout.addWidget(row)

            grand_total += seconds

        # Daily Total Separator
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #E2E8F0;")
        daily_layout.addWidget(line)

        total_row = QWidget()
        tot_layout = QHBoxLayout(total_row)
        tot_layout.setContentsMargins(0, 4, 0, 0)
        lbl_tot = QLabel("Week Total")
        lbl_tot.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        lbl_tot_dur = QLabel(format_duration(grand_total))
        lbl_tot_dur.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        lbl_tot_dur.setStyleSheet("color: #16A34A;")
        tot_layout.addWidget(lbl_tot)
        tot_layout.addStretch()
        tot_layout.addWidget(lbl_tot_dur)
        daily_layout.addWidget(total_row)

        layout.addWidget(daily_card)

        # Project Summary
        monday = today - timedelta(days=today.weekday())
        sunday = monday + timedelta(days=6)
        projects = self.engine.project_summary(monday, sunday)

        if projects:
            proj_title = QLabel("📁 PROJECT SUMMARY")
            proj_title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
            proj_title.setStyleSheet("color: #0F172A;")
            layout.addWidget(proj_title)

            proj_card = QFrame()
            proj_card.setProperty("class", "card")
            proj_layout = QVBoxLayout(proj_card)
            proj_layout.setSpacing(6)

            for activity, secs in sorted(projects.items(), key=lambda x: -x[1]):
                p_row = QWidget()
                p_layout = QHBoxLayout(p_row)
                p_layout.setContentsMargins(0, 2, 0, 2)
                lbl_act = QLabel(activity)
                lbl_act.setFont(QFont("Segoe UI", 10))
                lbl_act_dur = QLabel(format_duration(secs))
                lbl_act_dur.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
                lbl_act_dur.setStyleSheet("color: #334155;")
                p_layout.addWidget(lbl_act)
                p_layout.addStretch()
                p_layout.addWidget(lbl_act_dur)
                proj_layout.addWidget(p_row)

            layout.addWidget(proj_card)

        layout.addStretch()
