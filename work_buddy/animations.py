"""Canvas-based bot animations for Work Buddy."""

from __future__ import annotations

import random
import tkinter as tk
from typing import Callable

from .models import BotState

# Chroma-key color for Windows desktop transparency
TRANSPARENT = "#01FF01"
BOT_TAG = "bot_drawing"


def draw_rounded_rect(
    canvas: tk.Canvas,
    x1: float, y1: float, x2: float, y2: float,
    radius: float = 12,
    **kwargs,
) -> int:
    """Draw a smooth rounded rectangle on canvas."""
    points = [
        x1 + radius, y1,
        x2 - radius, y1,
        x2, y1, x2, y1 + radius,
        x2, y2 - radius,
        x2, y2, x2 - radius, y2,
        x1 + radius, y2,
        x1, y2, x1, y2 - radius,
        x1, y1 + radius,
        x1, y1, x1 + radius, y1,
    ]
    return canvas.create_polygon(points, smooth=True, **kwargs)


class AnimationController:
    """Draws and animates the bot character on a Tkinter Canvas.

    In collapsed mode: renders the floating animated head with a high-contrast
    digital timer pill badge underneath.
    In expanded mode: renders the full companion character with head, ears,
    paws, feet, and a soft warm tummy area where controls sit.
    """

    # Palette
    BODY_COLOR = "#FFD93D"
    BODY_BORDER = "#F5A623"
    TUMMY_COLOR = "#FFFBEB"
    TUMMY_BORDER = "#FDE68A"
    EYE_COLOR = "#1E293B"
    SMILE_COLOR = "#E11D48"
    CHEEK_COLOR = "#FDA4AF"
    ZZZ_COLOR = "#64748B"

    # High-contrast timer badge palette
    TIMER_BG = "#0F172A"
    TIMER_BORDER_WORKING = "#10B981"
    TIMER_BORDER_STOPPED = "#334155"
    TIMER_DIGIT_WORKING = "#22C55E"
    TIMER_DIGIT_STOPPED = "#F1F5F9"

    def __init__(
        self,
        canvas: tk.Canvas,
        enabled: bool = True,
        wander_callback: Callable[[int, int], None] | None = None,
    ) -> None:
        self.canvas = canvas
        self.enabled = enabled
        self.wander_callback = wander_callback
        self.state = BotState.STOPPED
        self.can_wander = True
        self.is_expanded = False

        # Timer text drawn on the canvas (collapsed mode)
        self._timer_text: str = "00:00:00"
        self._timer_active: bool = False

        # Internal animation state
        self._is_blinking = False
        self._bounce_offset = 0
        self._zzz_phase = 0
        self._scheduled: list[str] = []

        # Geometry
        self.cx = 75
        self.cy = 44
        self.radius = 32

        self.draw()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_state(self, new_state: BotState) -> None:
        """Transition to a new visual state."""
        if new_state == self.state:
            return
        self.state = new_state
        self._cancel_all()
        self._is_blinking = False
        self._bounce_offset = 0
        self._zzz_phase = 0
        self.draw()
        if self.enabled:
            self._schedule_animations()

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = enabled
        self._cancel_all()
        if enabled:
            self._schedule_animations()

    def set_expanded_mode(self, expanded: bool, cx: int) -> None:
        """Toggle between collapsed head-only and expanded full-body mode."""
        self.is_expanded = expanded
        self.cx = cx
        self.draw()

    def update_timer(self, text: str, active: bool) -> None:
        """Update the timer text and redraw if changed."""
        if text != self._timer_text or active != self._timer_active:
            self._timer_text = text
            self._timer_active = active
            self.draw()

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------

    def draw(self) -> None:
        """Redraw the bot character (tagged with BOT_TAG)."""
        self.canvas.delete(BOT_TAG)
        cx = self.cx
        cy = self.cy + self._bounce_offset
        r = self.radius

        if self.is_expanded:
            self._draw_expanded_body(cx, cy)
        else:
            self._draw_collapsed_companion(cx, cy, r)

    def _draw_collapsed_companion(self, cx: int, cy: int, r: int) -> None:
        """Draw the cute floating head + high-contrast digital timer pill."""
        # --- Head Shadow (subtle) ---
        self.canvas.create_oval(
            cx - r + 2, cy - r + 3, cx + r + 2, cy + r + 3,
            fill="#E0C830", outline="", tags=BOT_TAG,
        )

        # --- Head Base ---
        self.canvas.create_oval(
            cx - r, cy - r, cx + r, cy + r,
            fill=self.BODY_COLOR, outline=self.BODY_BORDER, width=2.5,
            tags=BOT_TAG,
        )

        # --- Cheeks (working only) ---
        if self.state == BotState.WORKING:
            self.canvas.create_oval(
                cx - r + 3, cy + 7, cx - r + 14, cy + 16,
                fill=self.CHEEK_COLOR, outline="", tags=BOT_TAG,
            )
            self.canvas.create_oval(
                cx + r - 14, cy + 7, cx + r - 3, cy + 16,
                fill=self.CHEEK_COLOR, outline="", tags=BOT_TAG,
            )

        # --- Face Features ---
        self._draw_eyes(cx, cy)
        self._draw_mouth(cx, cy)

        if self.state == BotState.SLEEPING:
            self._draw_zzz(cx, cy, r)

        # --- High-Contrast Digital Timer Pill Badge ---
        # Deep dark background pill guarantees readability on ANY wallpaper!
        pill_w = 110
        pill_h = 30
        x1 = cx - pill_w // 2
        y1 = cy + r + 10
        x2 = cx + pill_w // 2
        y2 = y1 + pill_h

        border_col = (
            self.TIMER_BORDER_WORKING if self._timer_active else self.TIMER_BORDER_STOPPED
        )
        draw_rounded_rect(
            self.canvas, x1, y1, x2, y2, radius=10,
            fill=self.TIMER_BG, outline=border_col, width=1.5,
            tags=BOT_TAG,
        )

        # Tiny status LED dot inside the pill
        dot_color = self.TIMER_DIGIT_WORKING if self._timer_active else "#64748B"
        self.canvas.create_oval(
            x1 + 10, y1 + pill_h // 2 - 3, x1 + 16, y1 + pill_h // 2 + 3,
            fill=dot_color, outline="", tags=BOT_TAG,
        )

        # Crisp digital digits
        text_color = (
            self.TIMER_DIGIT_WORKING if self._timer_active else self.TIMER_DIGIT_STOPPED
        )
        self.canvas.create_text(
            cx + 6, y1 + pill_h // 2,
            text=self._timer_text,
            font=("Consolas", 12, "bold"), fill=text_color,
            tags=BOT_TAG,
        )

    def _draw_expanded_body(self, cx: int, cy: int) -> None:
        """Draw the full character body with belly/tummy contour."""
        r = self.radius

        # --- Cute Ears ---
        self.canvas.create_oval(
            cx - 28, cy - 36, cx - 14, cy - 20,
            fill=self.BODY_BORDER, outline=self.BODY_COLOR, width=1.5,
            tags=BOT_TAG,
        )
        self.canvas.create_oval(
            cx + 14, cy - 36, cx + 28, cy - 20,
            fill=self.BODY_BORDER, outline=self.BODY_COLOR, width=1.5,
            tags=BOT_TAG,
        )

        # --- Feet ---
        draw_rounded_rect(
            self.canvas, cx - 75, 395, cx - 25, 415, radius=8,
            fill=self.BODY_BORDER, outline="", tags=BOT_TAG,
        )
        draw_rounded_rect(
            self.canvas, cx + 25, 395, cx + 75, 415, radius=8,
            fill=self.BODY_BORDER, outline="", tags=BOT_TAG,
        )

        # --- Outer Body (Yellow character shape) ---
        draw_rounded_rect(
            self.canvas, 14, 45, 246, 405, radius=32,
            fill=self.BODY_COLOR, outline=self.BODY_BORDER, width=2.5,
            tags=BOT_TAG,
        )

        # --- Cute Paws on sides ---
        draw_rounded_rect(
            self.canvas, 6, 145, 22, 190, radius=8,
            fill=self.BODY_BORDER, outline="", tags=BOT_TAG,
        )
        draw_rounded_rect(
            self.canvas, 238, 145, 254, 190, radius=8,
            fill=self.BODY_BORDER, outline="", tags=BOT_TAG,
        )

        # --- Inner Cream Tummy (The Belly Area) ---
        draw_rounded_rect(
            self.canvas, 24, 88, 236, 395, radius=22,
            fill=self.TUMMY_COLOR, outline=self.TUMMY_BORDER, width=2,
            tags=BOT_TAG,
        )

        # --- Head Base ---
        self.canvas.create_oval(
            cx - r, cy - r, cx + r, cy + r,
            fill=self.BODY_COLOR, outline=self.BODY_BORDER, width=2,
            tags=BOT_TAG,
        )

        # --- Cheeks (working only) ---
        if self.state == BotState.WORKING:
            self.canvas.create_oval(
                cx - r + 3, cy + 7, cx - r + 14, cy + 16,
                fill=self.CHEEK_COLOR, outline="", tags=BOT_TAG,
            )
            self.canvas.create_oval(
                cx + r - 14, cy + 7, cx + r - 3, cy + 16,
                fill=self.CHEEK_COLOR, outline="", tags=BOT_TAG,
            )

        # --- Face Features ---
        self._draw_eyes(cx, cy)
        self._draw_mouth(cx, cy)

        if self.state == BotState.SLEEPING:
            self._draw_zzz(cx, cy, r)

    def _draw_eyes(self, cx: int, cy: int) -> None:
        if self.state == BotState.SLEEPING:
            self.canvas.create_arc(
                cx - 16, cy - 10, cx - 4, cy + 2,
                start=0, extent=180, style="arc", width=2, outline=self.EYE_COLOR,
                tags=BOT_TAG,
            )
            self.canvas.create_arc(
                cx + 4, cy - 10, cx + 16, cy + 2,
                start=0, extent=180, style="arc", width=2, outline=self.EYE_COLOR,
                tags=BOT_TAG,
            )
        elif self._is_blinking:
            self.canvas.create_line(
                cx - 15, cy - 4, cx - 5, cy - 4, width=2.5, fill=self.EYE_COLOR,
                tags=BOT_TAG,
            )
            self.canvas.create_line(
                cx + 5, cy - 4, cx + 15, cy - 4, width=2.5, fill=self.EYE_COLOR,
                tags=BOT_TAG,
            )
        elif self.state == BotState.IDLE:
            self.canvas.create_oval(
                cx - 14, cy - 5, cx - 6, cy + 2, fill=self.EYE_COLOR, outline="",
                tags=BOT_TAG,
            )
            self.canvas.create_oval(
                cx + 6, cy - 5, cx + 14, cy + 2, fill=self.EYE_COLOR, outline="",
                tags=BOT_TAG,
            )
        else:
            # Open energetic eyes
            self.canvas.create_oval(
                cx - 15, cy - 11, cx - 5, cy + 1, fill=self.EYE_COLOR, outline="",
                tags=BOT_TAG,
            )
            self.canvas.create_oval(
                cx + 5, cy - 11, cx + 15, cy + 1, fill=self.EYE_COLOR, outline="",
                tags=BOT_TAG,
            )
            # Highlights
            self.canvas.create_oval(
                cx - 13, cy - 10, cx - 8, cy - 5, fill="white", outline="",
                tags=BOT_TAG,
            )
            self.canvas.create_oval(
                cx + 7, cy - 10, cx + 12, cy - 5, fill="white", outline="",
                tags=BOT_TAG,
            )

    def _draw_mouth(self, cx: int, cy: int) -> None:
        if self.state == BotState.WORKING:
            self.canvas.create_arc(
                cx - 11, cy + 2, cx + 11, cy + 20,
                start=200, extent=140, style="arc",
                width=2.5, outline=self.SMILE_COLOR,
                tags=BOT_TAG,
            )
        elif self.state == BotState.SLEEPING:
            self.canvas.create_oval(
                cx - 4, cy + 10, cx + 4, cy + 17,
                fill=self.EYE_COLOR, outline="",
                tags=BOT_TAG,
            )
        else:
            self.canvas.create_line(
                cx - 8, cy + 13, cx + 8, cy + 13,
                width=2, fill=self.EYE_COLOR,
                tags=BOT_TAG,
            )

    def _draw_zzz(self, cx: int, cy: int, r: int) -> None:
        phase = self._zzz_phase % 40
        specs = [
            (cx + r - 2, cy - r + 8 - phase * 0.5, 7),
            (cx + r + 4, cy - r - 2 - phase * 0.5, 9),
            (cx + r + 10, cy - r - 12 - phase * 0.5, 11),
        ]
        for x, y, size in specs:
            if cy - r - 30 < y < cy + r:
                self.canvas.create_text(
                    x, y, text="z",
                    font=("Segoe UI", size, "italic"),
                    fill=self.ZZZ_COLOR,
                    tags=BOT_TAG,
                )

    # ------------------------------------------------------------------
    # Animation scheduling
    # ------------------------------------------------------------------

    def _schedule_animations(self) -> None:
        if self.state == BotState.SLEEPING:
            self._schedule_zzz()
            self._schedule_blink()
        else:
            self._schedule_blink()
        if self.state == BotState.WORKING:
            self._schedule_bounce()
        if self.state in (BotState.STOPPED, BotState.IDLE) and self.can_wander:
            self._schedule_wander()

    # -- Blink --

    def _schedule_blink(self) -> None:
        lo, hi = (3000, 6000) if self.state == BotState.WORKING else (4000, 8000)
        aid = self.canvas.after(random.randint(lo, hi), self._do_blink)
        self._scheduled.append(aid)

    def _do_blink(self) -> None:
        self._is_blinking = True
        self.draw()
        aid = self.canvas.after(150, self._end_blink)
        self._scheduled.append(aid)

    def _end_blink(self) -> None:
        self._is_blinking = False
        self.draw()
        if self.enabled:
            self._schedule_blink()

    # -- Bounce --

    def _schedule_bounce(self) -> None:
        aid = self.canvas.after(random.randint(12000, 25000), self._do_bounce_up)
        self._scheduled.append(aid)

    def _do_bounce_up(self) -> None:
        self._bounce_offset = -4
        self.draw()
        aid = self.canvas.after(150, self._do_bounce_down)
        self._scheduled.append(aid)

    def _do_bounce_down(self) -> None:
        self._bounce_offset = 0
        self.draw()
        if self.enabled and self.state == BotState.WORKING:
            self._schedule_bounce()

    # -- Sleeping zzz --

    def _schedule_zzz(self) -> None:
        aid = self.canvas.after(250, self._do_zzz)
        self._scheduled.append(aid)

    def _do_zzz(self) -> None:
        self._zzz_phase = (self._zzz_phase + 1) % 80
        self.draw()
        if self.enabled and self.state == BotState.SLEEPING:
            self._schedule_zzz()

    # -- Wander --

    def _schedule_wander(self) -> None:
        aid = self.canvas.after(random.randint(30000, 60000), self._do_wander)
        self._scheduled.append(aid)

    def _do_wander(self) -> None:
        if self.wander_callback and self.can_wander:
            dx = random.randint(-15, 15)
            dy = random.randint(-10, 10)
            self.wander_callback(dx, dy)
        if (
            self.enabled
            and self.state in (BotState.STOPPED, BotState.IDLE)
            and self.can_wander
        ):
            self._schedule_wander()

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def _cancel_all(self) -> None:
        for aid in self._scheduled:
            try:
                self.canvas.after_cancel(aid)
            except (ValueError, tk.TclError):
                pass
        self._scheduled.clear()
