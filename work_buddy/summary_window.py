"""Weekly summary window for Work Buddy."""

from __future__ import annotations

import tkinter as tk
from datetime import timedelta
from tkinter import ttk

from .models import format_duration
from .timer_engine import TimerEngine

# Local color scheme (matches bot_window)
_BG = "#F0F4F8"
_TEXT = "#2C3E50"
_TEXT_LIGHT = "#7F8C8D"
_ACCENT = "#3498DB"
_HEADER = "#2C3E50"

_DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


class SummaryWindow:
    """Toplevel window showing the current week's daily and project totals."""

    def __init__(self, parent: tk.Tk, engine: TimerEngine) -> None:
        self.engine = engine

        self.window = tk.Toplevel(parent)
        self.window.title("Weekly Summary — Work Buddy")
        self.window.geometry("320x480")
        self.window.attributes("-topmost", True)
        self.window.resizable(False, False)
        self.window.configure(bg=_BG)

        self._build_daily_section()
        self._build_project_section()

    # ------------------------------------------------------------------
    # Daily breakdown
    # ------------------------------------------------------------------

    def _build_daily_section(self) -> None:
        tk.Label(
            self.window, text="THIS WEEK",
            font=("Segoe UI", 12, "bold"), fg=_HEADER, bg=_BG,
        ).pack(pady=(15, 5))

        week = self.engine.week_summary()
        frame = tk.Frame(self.window, bg=_BG)
        frame.pack(fill="x", padx=30)

        grand_total = 0
        today = self.engine.clock().date()
        for d, seconds in sorted(week.items()):
            is_today = d == today
            day_name = _DAY_NAMES[d.weekday()]
            dur = format_duration(seconds)

            row = tk.Frame(frame, bg=_BG)
            row.pack(fill="x", pady=1)

            font = ("Segoe UI", 10, "bold") if is_today else ("Segoe UI", 10)
            fg = _ACCENT if is_today else _TEXT

            tk.Label(
                row, text=day_name, font=font, fg=fg, bg=_BG, width=5, anchor="w",
            ).pack(side="left")
            tk.Label(
                row, text=dur, font=font, fg=fg, bg=_BG, anchor="e",
            ).pack(side="right")

            grand_total += seconds

        # Separator + total
        ttk.Separator(frame, orient="horizontal").pack(fill="x", pady=5)
        total_row = tk.Frame(frame, bg=_BG)
        total_row.pack(fill="x")
        tk.Label(
            total_row, text="Total",
            font=("Segoe UI", 10, "bold"), fg=_HEADER, bg=_BG, width=5, anchor="w",
        ).pack(side="left")
        tk.Label(
            total_row, text=format_duration(grand_total),
            font=("Segoe UI", 10, "bold"), fg=_HEADER, bg=_BG, anchor="e",
        ).pack(side="right")

    # ------------------------------------------------------------------
    # Project breakdown
    # ------------------------------------------------------------------

    def _build_project_section(self) -> None:
        today = self.engine.clock().date()
        monday = today - timedelta(days=today.weekday())
        sunday = monday + timedelta(days=6)
        projects = self.engine.project_summary(monday, sunday)

        if not projects:
            return

        tk.Label(
            self.window, text="PROJECT SUMMARY",
            font=("Segoe UI", 12, "bold"), fg=_HEADER, bg=_BG,
        ).pack(pady=(20, 5))

        frame = tk.Frame(self.window, bg=_BG)
        frame.pack(fill="x", padx=30)

        grand_total = 0
        for activity, seconds in sorted(projects.items(), key=lambda x: -x[1]):
            row = tk.Frame(frame, bg=_BG)
            row.pack(fill="x", pady=1)
            tk.Label(
                row, text=activity, font=("Segoe UI", 10), fg=_TEXT, bg=_BG, anchor="w",
            ).pack(side="left")
            tk.Label(
                row, text=format_duration(seconds),
                font=("Segoe UI", 10), fg=_TEXT, bg=_BG, anchor="e",
            ).pack(side="right")
            grand_total += seconds

        ttk.Separator(frame, orient="horizontal").pack(fill="x", pady=5)
        total_row = tk.Frame(frame, bg=_BG)
        total_row.pack(fill="x")
        tk.Label(
            total_row, text="Total",
            font=("Segoe UI", 10, "bold"), fg=_HEADER, bg=_BG, anchor="w",
        ).pack(side="left")
        tk.Label(
            total_row, text=format_duration(grand_total),
            font=("Segoe UI", 10, "bold"), fg=_HEADER, bg=_BG, anchor="e",
        ).pack(side="right")
