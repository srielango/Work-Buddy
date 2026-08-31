"""Main bot window GUI for Work Buddy.

Uses Windows' ``-transparentcolor`` so the smiley companion floats directly
on the desktop. In expanded mode, the character reveals its full body and
tummy, with the controls and high-contrast digital timer embedded directly
into the character's belly.
"""

from __future__ import annotations

import calendar
import logging
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .animations import AnimationController, BOT_TAG, TRANSPARENT
from .excel_export import ExcelExporter
from .models import BotState, format_duration, format_timer
from .settings import Settings
from .summary_window import SummaryWindow
from .timer_engine import TimerEngine

logger = logging.getLogger("workbuddy")

# ---------------------------------------------------------------------------
# Tummy & Widget Styling
# ---------------------------------------------------------------------------
COLORS = {
    "tummy_bg": "#FFFBEB",
    "text": "#1E293B",
    "text_muted": "#64748B",
    "accent": "#3B82F6",
    "start_bg": "#16A34A",
    "start_hover": "#22C55E",
    "stop_bg": "#DC2626",
    "stop_hover": "#EF4444",
    "lcd_bg": "#0F172A",
    "lcd_border": "#334155",
    "lcd_working": "#22C55E",
    "lcd_stopped": "#F8FAFC",
    "toolbar_bg": "#FEF3C7",
}


class BotWindow:
    """The always-on-top animated bot companion.

    * **Collapsed**: floating character head + high-contrast digital timer pill.
    * **Expanded**: full character body with belly, timer LCD, and belly start/stop button.
    * Click the character head to toggle expand/collapse.
    * Drag the character to reposition anywhere on screen.
    """

    COLLAPSED_W = 150
    COLLAPSED_H = 135
    EXPANDED_W = 260
    EXPANDED_H = 440

    def __init__(
        self,
        root: tk.Tk,
        engine: TimerEngine,
        settings: Settings,
        data_dir: Path,
    ) -> None:
        self.root = root
        self.engine = engine
        self.settings = settings
        self.data_dir = data_dir
        self.expanded = False

        # Drag state
        self._dragged = False
        self._drag_x = 0
        self._drag_y = 0

        # Canvas window item id for the embedded tummy panel
        self._panel_window_id: int | None = None

        # Idle tracking (for animation state transitions)
        self._idle_since: datetime | None = (
            None if engine.is_working else datetime.now()
        )

        # Child windows
        self._summary_win: SummaryWindow | None = None
        self._restore_dot: tk.Toplevel | None = None

        self._setup_window()
        self._create_widgets()
        self._setup_animation()
        self._update_display()

    # ------------------------------------------------------------------
    # Window setup — transparent background
    # ------------------------------------------------------------------

    def _setup_window(self) -> None:
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", self.settings.always_on_top)
        self.root.configure(bg=TRANSPARENT)
        self.root.attributes("-transparentcolor", TRANSPARENT)
        self.root.resizable(False, False)

        # Initial position
        if self.settings.bot_x is not None and self.settings.bot_y is not None:
            self.root.geometry(f"+{self.settings.bot_x}+{self.settings.bot_y}")
        else:
            sw = self.root.winfo_screenwidth()
            sh = self.root.winfo_screenheight()
            x = sw - self.COLLAPSED_W - 60
            y = sh - self.COLLAPSED_H - 120
            self.root.geometry(f"+{x}+{y}")

        self._set_size(self.COLLAPSED_W, self.COLLAPSED_H)
        self.root.protocol("WM_DELETE_WINDOW", self.on_exit)

    def _set_size(self, w: int, h: int) -> None:
        x = self.root.winfo_x()
        y = self.root.winfo_y()
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    # ------------------------------------------------------------------
    # Widget creation
    # ------------------------------------------------------------------

    def _create_widgets(self) -> None:
        # Full transparent canvas for the character
        self.canvas = tk.Canvas(
            self.root, width=self.COLLAPSED_W, height=self.COLLAPSED_H,
            bg=TRANSPARENT, highlightthickness=0,
        )
        self.canvas.pack(fill="both", expand=True)

        # Mouse bindings for drag / click
        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_motion)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)

        # Build the tummy control frame (embedded inside belly when expanded)
        self._build_tummy_panel()

    def _build_tummy_panel(self) -> None:
        """Create controls embedded inside the character's tummy."""
        pf = tk.Frame(
            self.root, bg=COLORS["tummy_bg"],
            highlightthickness=0, bd=0,
        )
        self._panel_frame = pf

        # Status badge
        self.status_label = tk.Label(
            pf, text="● READY",
            font=("Segoe UI", 9, "bold"),
            fg=COLORS["text_muted"], bg=COLORS["tummy_bg"],
        )
        self.status_label.pack(pady=(2, 4))

        # High-contrast Digital LCD Timer Badge
        lcd_frame = tk.Frame(
            pf, bg=COLORS["lcd_bg"],
            highlightthickness=1, highlightbackground=COLORS["lcd_border"],
            padx=12, pady=4,
        )
        lcd_frame.pack(pady=(0, 6))

        self.lcd_timer_label = tk.Label(
            lcd_frame, text="00:00:00",
            font=("Consolas", 16, "bold"),
            fg=COLORS["lcd_stopped"], bg=COLORS["lcd_bg"],
        )
        self.lcd_timer_label.pack()

        # Activity selector
        act_frame = tk.Frame(pf, bg=COLORS["tummy_bg"])
        act_frame.pack(fill="x", padx=6, pady=(0, 4))
        tk.Label(
            act_frame, text="Activity:", font=("Segoe UI", 8, "bold"),
            fg=COLORS["text_muted"], bg=COLORS["tummy_bg"],
        ).pack(anchor="w")

        self.activity_var = tk.StringVar()
        self.activity_combo = ttk.Combobox(
            act_frame, textvariable=self.activity_var,
            values=self.engine.recent_activities(),
            font=("Segoe UI", 9),
        )
        self.activity_combo.pack(fill="x", pady=(1, 0))

        # Start / Stop Belly Button
        self.toggle_btn = tk.Button(
            pf, text="▶ START",
            font=("Segoe UI", 11, "bold"),
            fg="white", bg=COLORS["start_bg"],
            activebackground=COLORS["start_hover"],
            activeforeground="white",
            relief="flat", cursor="hand2",
            width=11, pady=3,
            command=self._toggle_work,
        )
        self.toggle_btn.pack(pady=6)

        # Today total
        self.today_label = tk.Label(
            pf, text="Today: 0h 00m",
            font=("Segoe UI", 9, "bold"), fg=COLORS["text"], bg=COLORS["tummy_bg"],
        )
        self.today_label.pack(pady=(0, 6))

        # Bottom accessory toolbar
        toolbar = tk.Frame(pf, bg=COLORS["toolbar_bg"], padx=4, pady=2)
        toolbar.pack(fill="x", side="bottom")

        btn_kw: dict = dict(
            font=("Segoe UI", 10), bg=COLORS["toolbar_bg"],
            activebackground=COLORS["toolbar_bg"],
            relief="flat", cursor="hand2", bd=0,
        )
        tk.Button(toolbar, text="📊", command=self._show_summary, **btn_kw).pack(
            side="left", padx=4,
        )
        tk.Button(toolbar, text="📋", command=self._export_excel, **btn_kw).pack(
            side="left", padx=4,
        )
        tk.Button(toolbar, text="✕", command=self.on_exit, **btn_kw).pack(
            side="right", padx=4,
        )
        tk.Button(toolbar, text="─", command=self._minimize, **btn_kw).pack(
            side="right", padx=4,
        )

    # ------------------------------------------------------------------
    # Animation
    # ------------------------------------------------------------------

    def _setup_animation(self) -> None:
        def wander(dx: int, dy: int) -> None:
            if self.expanded:
                return
            x = max(0, self.root.winfo_x() + dx)
            y = max(0, self.root.winfo_y() + dy)
            sw = self.root.winfo_screenwidth()
            sh = self.root.winfo_screenheight()
            x = min(x, sw - self.COLLAPSED_W)
            y = min(y, sh - self.COLLAPSED_H)
            self.root.geometry(f"+{x}+{y}")

        self.animator = AnimationController(
            self.canvas,
            enabled=self.settings.animations_enabled,
            wander_callback=wander,
        )
        self.animator.cx = self.COLLAPSED_W // 2
        self.animator.draw()
        self._sync_bot_visual()

    def _sync_bot_visual(self) -> None:
        """Set the animator's visual state from engine state + idle time."""
        if self.engine.is_working:
            self.animator.set_state(BotState.WORKING)
            self._idle_since = None
            return

        if self._idle_since is None:
            self._idle_since = datetime.now()

        idle_min = (datetime.now() - self._idle_since).total_seconds() / 60
        if idle_min >= self.settings.sleep_minutes:
            self.animator.set_state(BotState.SLEEPING)
        elif idle_min >= self.settings.idle_minutes:
            self.animator.set_state(BotState.IDLE)
        else:
            self.animator.set_state(BotState.STOPPED)

    # ------------------------------------------------------------------
    # Drag / Click
    # ------------------------------------------------------------------

    def _on_press(self, event: tk.Event) -> None:
        self._drag_x = event.x_root
        self._drag_y = event.y_root
        self._dragged = False

    def _on_motion(self, event: tk.Event) -> None:
        dx = event.x_root - self._drag_x
        dy = event.y_root - self._drag_y
        if abs(dx) > 5 or abs(dy) > 5:
            self._dragged = True
            nx = self.root.winfo_x() + dx
            ny = self.root.winfo_y() + dy
            self.root.geometry(f"+{nx}+{ny}")
            self._drag_x = event.x_root
            self._drag_y = event.y_root

    def _on_release(self, event: tk.Event) -> None:
        if self._dragged:
            self._save_position()
        else:
            # If expanded, clicking the head area (y <= 85) collapses it
            if self.expanded and event.y > 85:
                return
            self._toggle_expand()

    def _save_position(self) -> None:
        self.settings.bot_x = self.root.winfo_x()
        self.settings.bot_y = self.root.winfo_y()

    # ------------------------------------------------------------------
    # Expand / Collapse
    # ------------------------------------------------------------------

    def _toggle_expand(self) -> None:
        if self.expanded:
            self._collapse()
        else:
            self._expand()

    def _expand(self) -> None:
        if self.expanded:
            return
        self.expanded = True
        self.animator.can_wander = False

        # 1. Resize window & canvas to full-body dimensions
        self._set_size(self.EXPANDED_W, self.EXPANDED_H)
        self.canvas.config(width=self.EXPANDED_W, height=self.EXPANDED_H)

        # 2. Draw full companion character body with belly
        self.animator.set_expanded_mode(True, self.EXPANDED_W // 2)

        # 3. Embed tummy control panel directly into the belly
        if self._panel_window_id is None:
            self._panel_window_id = self.canvas.create_window(
                self.EXPANDED_W // 2, 245,
                window=self._panel_frame,
                width=196, height=285,
            )
        else:
            self.canvas.itemconfigure(self._panel_window_id, state="normal")

        self._refresh_activity_list()
        self._sync_expanded_labels()

    def _collapse(self) -> None:
        if not self.expanded:
            return
        self.expanded = False
        self.animator.can_wander = True

        # 1. Hide the embedded tummy frame
        if self._panel_window_id is not None:
            self.canvas.itemconfigure(self._panel_window_id, state="hidden")

        # 2. Resize window & canvas back to collapsed size
        self._set_size(self.COLLAPSED_W, self.COLLAPSED_H)
        self.canvas.config(width=self.COLLAPSED_W, height=self.COLLAPSED_H)

        # 3. Redraw in collapsed head + digital pill mode
        self.animator.set_expanded_mode(False, self.COLLAPSED_W // 2)

    def _refresh_activity_list(self) -> None:
        self.activity_combo["values"] = self.engine.recent_activities()

    def _sync_expanded_labels(self) -> None:
        """Refresh status label and button to match engine state."""
        if self.engine.is_working:
            self.status_label.config(text="● WORKING", fg=COLORS["start_bg"])
            self.lcd_timer_label.config(fg=COLORS["lcd_working"])
            self.toggle_btn.config(
                text="⏹ STOP", bg=COLORS["stop_bg"],
                activebackground=COLORS["stop_hover"],
            )
            sess = self.engine.active_session
            if sess and sess.activity:
                self.activity_var.set(sess.activity)
        else:
            self.status_label.config(text="● READY", fg=COLORS["text_muted"])
            self.lcd_timer_label.config(fg=COLORS["lcd_stopped"])
            self.toggle_btn.config(
                text="▶ START", bg=COLORS["start_bg"],
                activebackground=COLORS["start_hover"],
            )

    # ------------------------------------------------------------------
    # Start / Stop
    # ------------------------------------------------------------------

    def _toggle_work(self) -> None:
        if self.engine.is_working:
            self.engine.stop()
            self._idle_since = datetime.now()
        else:
            self.engine.start(self.activity_var.get())
            self._idle_since = None
        self._sync_expanded_labels()
        self._sync_bot_visual()

    # ------------------------------------------------------------------
    # Display update loop (~500 ms)
    # ------------------------------------------------------------------

    def _update_display(self) -> None:
        try:
            self.engine.tick()

            if self.engine.is_working:
                elapsed = self.engine.elapsed()
                timer_str = format_timer(int(elapsed.total_seconds()))
                active = True
            else:
                timer_str = "00:00:00"
                active = False

            # Update timer on the collapsed pill badge
            self.animator.update_timer(timer_str, active)

            # Update timer on the expanded LCD display
            if self.expanded:
                self.lcd_timer_label.config(
                    text=timer_str,
                    fg=COLORS["lcd_working"] if active else COLORS["lcd_stopped"],
                )
                total = self.engine.today_total_seconds()
                self.today_label.config(text=f"Today: {format_duration(total)}")
                self._sync_expanded_labels()

            self._sync_bot_visual()
        except Exception:
            logger.exception("Error in display update")
        finally:
            self.root.after(500, self._update_display)

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def _show_summary(self) -> None:
        if (
            self._summary_win
            and self._summary_win.window.winfo_exists()
        ):
            self._summary_win.window.lift()
            return
        self._summary_win = SummaryWindow(self.root, self.engine)

    # ------------------------------------------------------------------
    # Excel export
    # ------------------------------------------------------------------

    def _export_excel(self) -> None:
        months = self.engine.available_months()
        if not months:
            messagebox.showinfo(
                "Export", "No data to export yet.", parent=self.root,
            )
            return
        _ExportDialog(self.root, self.engine, months)

    # ------------------------------------------------------------------
    # Minimize / Restore
    # ------------------------------------------------------------------

    def _minimize(self) -> None:
        x, y = self.root.winfo_x(), self.root.winfo_y()
        if self.expanded:
            self._collapse()
        self.root.withdraw()
        self._create_restore_dot(x, y)

    def _create_restore_dot(self, x: int, y: int) -> None:
        dot = tk.Toplevel()
        dot.overrideredirect(True)
        dot.attributes("-topmost", True)
        dot.configure(bg=TRANSPARENT)
        dot.attributes("-transparentcolor", TRANSPARENT)
        dot.geometry(f"40x40+{x}+{y}")

        c = tk.Canvas(dot, width=40, height=40, bg=TRANSPARENT, highlightthickness=0)
        c.pack()
        c.create_oval(4, 4, 36, 36, fill="#FFD93D", outline="#F5A623", width=2)
        c.create_oval(14, 14, 18, 18, fill="#1E293B", outline="")
        c.create_oval(22, 14, 26, 18, fill="#1E293B", outline="")
        c.create_arc(15, 20, 25, 28, start=200, extent=140, style="arc", width=2, outline="#E11D48")

        c.bind("<Button-1>", lambda _e: self._restore(dot))
        self._restore_dot = dot

    def _restore(self, dot: tk.Toplevel) -> None:
        dot.destroy()
        self._restore_dot = None
        self.root.deiconify()
        self.root.lift()
        self.root.attributes("-topmost", self.settings.always_on_top)

    # ------------------------------------------------------------------
    # Exit
    # ------------------------------------------------------------------

    def on_exit(self) -> None:
        if self.engine.is_working:
            proceed = messagebox.askyesno(
                "Work Buddy",
                "A session is active. Exit anyway?\n\n"
                "The session will be saved and recovered next time.",
                parent=self.root,
            )
            if not proceed:
                return

        self._save_position()
        self.settings.save(self.data_dir / "settings.json")
        self.engine.storage.save(self.engine.worklog)
        logger.info("Work Buddy exiting")

        if self._restore_dot:
            self._restore_dot.destroy()
        self.root.destroy()


# ======================================================================
# Export dialog
# ======================================================================

class _ExportDialog:
    """Simple month-picker dialog for Excel export."""

    def __init__(
        self,
        parent: tk.Tk,
        engine: TimerEngine,
        months: list[tuple[int, int]],
    ) -> None:
        self.engine = engine
        self.months = months

        self.window = tk.Toplevel(parent)
        self.window.title("Export to Excel")
        self.window.geometry("300x200")
        self.window.attributes("-topmost", True)
        self.window.resizable(False, False)
        self.window.configure(bg="#F0F4F8")

        tk.Label(
            self.window, text="Select month to export:",
            font=("Segoe UI", 10), bg="#F0F4F8",
        ).pack(pady=(20, 8))

        self.month_var = tk.StringVar()
        month_labels = [
            f"{calendar.month_name[m]} {y}" for y, m in months
        ]
        self.month_combo = ttk.Combobox(
            self.window, textvariable=self.month_var,
            values=month_labels, state="readonly", font=("Segoe UI", 10),
        )
        self.month_combo.pack(padx=30, fill="x")
        if month_labels:
            self.month_combo.current(len(month_labels) - 1)

        tk.Button(
            self.window, text="Export",
            font=("Segoe UI", 10, "bold"),
            bg=COLORS["accent"], fg="white",
            activebackground=COLORS["accent"], activeforeground="white",
            relief="flat", cursor="hand2", pady=4,
            command=self._do_export,
        ).pack(pady=20)

    def _do_export(self) -> None:
        idx = self.month_combo.current()
        if idx < 0:
            return
        year, month = self.months[idx]
        filename = f"{calendar.month_name[month]} {year}.xlsx"

        output = filedialog.asksaveasfilename(
            parent=self.window,
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")],
            initialfile=filename,
            initialdir=str(Path.home() / "Documents"),
        )
        if not output:
            return

        try:
            ExcelExporter().export_month(
                self.engine.worklog, year, month, Path(output),
            )
            messagebox.showinfo(
                "Export", f"Exported successfully to:\n{output}",
                parent=self.window,
            )
            logger.info("Excel export completed: %s", output)
            self.window.destroy()
        except PermissionError:
            messagebox.showerror(
                "Export Error",
                "Cannot write to that file.\n\n"
                "If the file is open in Excel, please close it and try again.",
                parent=self.window,
            )
        except Exception as exc:
            messagebox.showerror(
                "Export Error", f"Export failed:\n{exc}", parent=self.window,
            )
            logger.error("Excel export failed: %s", exc)
