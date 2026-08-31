"""Vector-based pet rendering engine for Work Buddy using PyQt6."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import List

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QRadialGradient,
)

from .models import AvatarType, BotState, ColorTheme


# ---------------------------------------------------------------------------
# Theme Palettes
# ---------------------------------------------------------------------------
THEMES = {
    ColorTheme.GOLDEN.value: {
        "primary": QColor("#F59E0B"),
        "secondary": QColor("#D97706"),
        "tummy": QColor("#FFFBEB"),
        "snout": QColor("#FDE68A"),
        "accent": QColor("#B45309"),
        "ear_inner": QColor("#FDA4AF"),
    },
    ColorTheme.SNOW.value: {
        "primary": QColor("#F8FAFC"),
        "secondary": QColor("#CBD5E1"),
        "tummy": QColor("#FFFFFF"),
        "snout": QColor("#E2E8F0"),
        "accent": QColor("#94A3B8"),
        "ear_inner": QColor("#FBCFE8"),
    },
    ColorTheme.CHOCOLATE.value: {
        "primary": QColor("#8D6E63"),
        "secondary": QColor("#5D4037"),
        "tummy": QColor("#EFEBE9"),
        "snout": QColor("#D7CCC8"),
        "accent": QColor("#4E342E"),
        "ear_inner": QColor("#F48FB1"),
    },
    ColorTheme.MIDNIGHT.value: {
        "primary": QColor("#1E293B"),
        "secondary": QColor("#0F172A"),
        "tummy": QColor("#334155"),
        "snout": QColor("#475569"),
        "accent": QColor("#64748B"),
        "ear_inner": QColor("#FB7185"),
    },
    ColorTheme.SAKURA.value: {
        "primary": QColor("#F472B6"),
        "secondary": QColor("#DB2777"),
        "tummy": QColor("#FDF2F8"),
        "snout": QColor("#FCE7F3"),
        "accent": QColor("#BE185D"),
        "ear_inner": QColor("#F43F5E"),
    },
    ColorTheme.CYBER.value: {
        "primary": QColor("#10B981"),
        "secondary": QColor("#047857"),
        "tummy": QColor("#ECFDF5"),
        "snout": QColor("#A7F3D0"),
        "accent": QColor("#065F46"),
        "ear_inner": QColor("#6EE7B7"),
    },
}


# ---------------------------------------------------------------------------
# Particle System
# ---------------------------------------------------------------------------
@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    alpha: float = 1.0
    size: float = 14.0
    text: str = "❤️"
    life: float = 1.0  # seconds


class ParticleSystem:
    """Manages floating hearts, sparkles, and sleep zzz particles."""

    def __init__(self) -> None:
        self.particles: List[Particle] = []

    def spawn_heart(self, x: float, y: float) -> None:
        p = Particle(
            x=x + random.uniform(-15, 15),
            y=y + random.uniform(-10, 5),
            vx=random.uniform(-0.5, 0.5),
            vy=random.uniform(-1.5, -2.5),
            alpha=1.0,
            size=random.uniform(14, 20),
            text=random.choice(["❤️", "💖", "✨", "⭐"]),
            life=random.uniform(1.0, 1.6),
        )
        self.particles.append(p)

    def spawn_zzz(self, x: float, y: float) -> None:
        p = Particle(
            x=x + random.uniform(5, 15),
            y=y - 10,
            vx=random.uniform(0.3, 0.8),
            vy=random.uniform(-0.8, -1.4),
            alpha=0.9,
            size=random.uniform(12, 16),
            text="z",
            life=2.0,
        )
        self.particles.append(p)

    def update(self, dt: float) -> None:
        survivors = []
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.alpha -= dt / p.life
            if p.alpha > 0.05:
                survivors.append(p)
        self.particles = survivors

    def draw(self, painter: QPainter) -> None:
        for p in self.particles:
            painter.save()
            painter.setOpacity(max(0.0, min(1.0, p.alpha)))
            font = QFont("Segoe UI Emoji", int(p.size))
            if p.text == "z":
                font = QFont("Segoe UI", int(p.size), QFont.Weight.Bold)
                font.setItalic(True)
                painter.setPen(QColor(100, 149, 237))  # cornflower blue
            painter.setFont(font)
            painter.drawText(QPointF(p.x, p.y), p.text)
            painter.restore()


# ---------------------------------------------------------------------------
# Pet Painter
# ---------------------------------------------------------------------------
class PetPainter:
    """Renders the animated pet character with 60fps vector precision."""

    def __init__(self) -> None:
        self.particles = ParticleSystem()
        self.avatar = AvatarType.DOG.value
        self.theme_name = ColorTheme.GOLDEN.value
        self.state = BotState.STOPPED

        # Animation states
        self.walk_phase = 0.0
        self.is_walking = False
        self.facing_left = False
        self.is_held = False
        self.is_blinking = False
        self.tail_phase = 0.0
        self.bounce_y = 0.0
        self.whisker_twitch = 0.0

    @property
    def theme(self) -> dict:
        return THEMES.get(self.theme_name, THEMES[ColorTheme.GOLDEN.value])

    def draw_pet(
        self,
        painter: QPainter,
        cx: float,
        cy: float,
        radius: float = 30.0,
        is_expanded: bool = False,
        timer_text: str = "00:00:00",
        timer_active: bool = False,
    ) -> None:
        """Main entry point to draw the pet character."""
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        # Draw floating particles in background
        self.particles.draw(painter)

        # Vertical bounce from walking or happy working state
        effective_cy = cy + self.bounce_y

        if is_expanded:
            self._draw_expanded_character(painter, cx, effective_cy, radius)
        else:
            # 1. Draw character body (mirrored if facing left)
            painter.save()
            if self.facing_left:
                painter.translate(cx * 2, 0)
                painter.scale(-1, 1)
            self._draw_collapsed_character_body(painter, cx, effective_cy, radius)
            painter.restore()

            # 2. Draw Digital Timer Pill (ALWAYS in normal un-mirrored coordinates)
            self._draw_timer_pill(painter, cx, effective_cy + radius + 16, timer_text, timer_active)

    # -----------------------------------------------------------------------
    # Collapsed Mode (Pet Body)
    # -----------------------------------------------------------------------
    def _draw_collapsed_character_body(
        self,
        painter: QPainter,
        cx: float,
        cy: float,
        r: float,
    ) -> None:
        t = self.theme

        # 1. Shadow beneath pet
        painter.save()
        shadow_grad = QRadialGradient(cx, cy + r + 4, r * 1.1)
        shadow_grad.setColorAt(0.0, QColor(0, 0, 0, 70))
        shadow_grad.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setBrush(QBrush(shadow_grad))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(cx, cy + r + 4), r * 0.9, r * 0.28)
        painter.restore()

        # 2. Tail (Dog/Cat)
        self._draw_tail(painter, cx, cy, r)

        # 3. Paws / Legs when walking or standing
        self._draw_collapsed_paws(painter, cx, cy, r)

        # 4. Head Base
        head_path = QPainterPath()
        head_path.addEllipse(QPointF(cx, cy), r, r)

        head_grad = QLinearGradient(cx - r, cy - r, cx + r, cy + r)
        head_grad.setColorAt(0.0, t["primary"].lighter(115))
        head_grad.setColorAt(1.0, t["primary"])

        painter.setBrush(QBrush(head_grad))
        painter.setPen(QPen(t["secondary"], 2.5))
        painter.drawPath(head_path)

        # 5. Ears / Antennas (Avatar-specific)
        self._draw_ears(painter, cx, cy, r)

        # 6. Face Details (Eyes, Cheeks, Snout, Mouth, Whiskers)
        self._draw_face_details(painter, cx, cy, r)

    # -----------------------------------------------------------------------
    # Expanded Mode (Full Character Body & Tummy)
    # -----------------------------------------------------------------------
    def _draw_expanded_character(
        self,
        painter: QPainter,
        cx: float,
        cy: float,
        r: float,
    ) -> None:
        t = self.theme

        # 1. Ears
        self._draw_ears(painter, cx, cy, r)

        # 2. Feet at bottom
        foot_w, foot_h = 42.0, 18.0
        painter.setBrush(QBrush(t["secondary"]))
        painter.setPen(QPen(t["accent"], 1.5))
        painter.drawRoundedRect(
            QRectF(cx - 75, 410, foot_w, foot_h), 8, 8
        )
        painter.drawRoundedRect(
            QRectF(cx + 33, 410, foot_w, foot_h), 8, 8
        )

        # 3. Outer Body (Warm rounded mascot body contour)
        body_rect = QRectF(14, 45, 232, 375)
        body_path = QPainterPath()
        body_path.addRoundedRect(body_rect, 34, 34)

        body_grad = QLinearGradient(14, 45, 246, 420)
        body_grad.setColorAt(0.0, t["primary"].lighter(110))
        body_grad.setColorAt(1.0, t["primary"])

        painter.setBrush(QBrush(body_grad))
        painter.setPen(QPen(t["secondary"], 2.8))
        painter.drawPath(body_path)

        # 4. Cute Paws on sides
        paw_w, paw_h = 16.0, 44.0
        painter.drawRoundedRect(QRectF(6, 140, paw_w, paw_h), 8, 8)
        painter.drawRoundedRect(QRectF(238, 140, paw_w, paw_h), 8, 8)

        # 5. Inner Cream Tummy Contour (Belly area where widgets live)
        tummy_rect = QRectF(24, 86, 212, 322)
        tummy_path = QPainterPath()
        tummy_path.addRoundedRect(tummy_rect, 22, 22)

        painter.setBrush(QBrush(t["tummy"]))
        painter.setPen(QPen(t["snout"], 2.0))
        painter.drawPath(tummy_path)

        # 6. Head
        head_path = QPainterPath()
        head_path.addEllipse(QPointF(cx, cy), r, r)
        painter.setBrush(QBrush(body_grad))
        painter.setPen(QPen(t["secondary"], 2.5))
        painter.drawPath(head_path)

        # 7. Face
        self._draw_face_details(painter, cx, cy, r)

    # -----------------------------------------------------------------------
    # Avatar-Specific Ears / Antennas
    # -----------------------------------------------------------------------
    def _draw_ears(self, painter: QPainter, cx: float, cy: float, r: float) -> None:
        t = self.theme
        avatar = self.avatar

        if avatar == AvatarType.DOG.value:
            # Floppy bouncy puppy ears
            ear_bounce = math.sin(self.walk_phase * math.pi * 2) * 5.0 if self.is_walking else 0.0
            ear_w, ear_h = 18.0, 36.0

            painter.save()
            painter.setBrush(QBrush(t["secondary"]))
            painter.setPen(QPen(t["accent"], 2.0))

            # Left floppy ear
            painter.translate(cx - r + 4, cy - r + 8 + ear_bounce)
            painter.rotate(-18 + ear_bounce)
            painter.drawRoundedRect(QRectF(-ear_w / 2, 0, ear_w, ear_h), 9, 9)
            painter.restore()

            # Right floppy ear
            painter.save()
            painter.translate(cx + r - 4, cy - r + 8 - ear_bounce)
            painter.rotate(18 - ear_bounce)
            painter.drawRoundedRect(QRectF(-ear_w / 2, 0, ear_w, ear_h), 9, 9)
            painter.restore()

        elif avatar == AvatarType.CAT.value:
            # Pointed alert cat ears with inner pink gradient
            left_ear = QPainterPath()
            left_ear.moveTo(cx - r + 4, cy - r + 14)
            left_ear.lineTo(cx - r + 2, cy - r - 16)
            left_ear.lineTo(cx - 8, cy - r + 4)
            left_ear.closeSubpath()

            right_ear = QPainterPath()
            right_ear.moveTo(cx + 8, cy - r + 4)
            right_ear.lineTo(cx + r - 2, cy - r - 16)
            right_ear.lineTo(cx + r - 4, cy - r + 14)
            right_ear.closeSubpath()

            painter.setBrush(QBrush(t["secondary"]))
            painter.setPen(QPen(t["accent"], 2.0))
            painter.drawPath(left_ear)
            painter.drawPath(right_ear)

            # Inner ear pink
            inner_left = QPainterPath()
            inner_left.moveTo(cx - r + 8, cy - r + 10)
            inner_left.lineTo(cx - r + 6, cy - r - 10)
            inner_left.lineTo(cx - 12, cy - r + 4)
            inner_left.closeSubpath()

            inner_right = QPainterPath()
            inner_right.moveTo(cx + 12, cy - r + 4)
            inner_right.lineTo(cx + r - 6, cy - r - 10)
            inner_right.lineTo(cx + r - 8, cy - r + 10)
            inner_right.closeSubpath()

            painter.setBrush(QBrush(t["ear_inner"]))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawPath(inner_left)
            painter.drawPath(inner_right)

        elif avatar == AvatarType.ROBOT.value:
            # Rotating beacon antenna + side audio bolts
            painter.setBrush(QBrush(QColor("#64748B")))
            painter.setPen(QPen(QColor("#334155"), 2.0))

            # Antenna pole
            painter.drawLine(int(cx), int(cy - r), int(cx), int(cy - r - 18))

            # Antenna glowing bulb
            bulb_color = QColor("#38BDF8") if self.state == BotState.WORKING else QColor("#94A3B8")
            painter.setBrush(QBrush(bulb_color))
            painter.drawEllipse(QPointF(cx, cy - r - 18), 6.0, 6.0)

            # Side bolts
            painter.setBrush(QBrush(QColor("#475569")))
            painter.drawRoundedRect(QRectF(cx - r - 6, cy - 6, 6, 12), 2, 2)
            painter.drawRoundedRect(QRectF(cx + r, cy - 6, 6, 12), 2, 2)

    # -----------------------------------------------------------------------
    # Tail & Walking Paws
    # -----------------------------------------------------------------------
    def _draw_tail(self, painter: QPainter, cx: float, cy: float, r: float) -> None:
        t = self.theme
        avatar = self.avatar
        if avatar not in (AvatarType.DOG.value, AvatarType.CAT.value):
            return

        tail_angle = math.sin(self.tail_phase) * (28.0 if self.state == BotState.WORKING else 14.0)

        painter.save()
        painter.translate(cx - r + 6, cy + r - 8)
        painter.rotate(-40 + tail_angle)

        tail_path = QPainterPath()
        tail_path.moveTo(0, 0)
        if avatar == AvatarType.DOG.value:
            tail_path.quadTo(-16, -14, -28, -8)
            tail_path.quadTo(-20, 2, 0, 0)
        else:
            tail_path.cubicTo(-14, -18, -26, -26, -32, -18)
            tail_path.cubicTo(-26, -12, -12, -8, 0, 0)

        painter.setBrush(QBrush(t["secondary"]))
        painter.setPen(QPen(t["accent"], 2.0))
        painter.drawPath(tail_path)
        painter.restore()

    def _draw_collapsed_paws(self, painter: QPainter, cx: float, cy: float, r: float) -> None:
        t = self.theme
        paw_w, paw_h = 14.0, 10.0

        if self.is_held:
            # Dangling paws when picked up
            painter.setBrush(QBrush(t["secondary"]))
            painter.setPen(QPen(t["accent"], 1.5))
            dangle = math.sin(self.walk_phase * math.pi * 4) * 4.0
            painter.drawRoundedRect(QRectF(cx - 20 + dangle, cy + r - 2, paw_w, paw_h + 4), 6, 6)
            painter.drawRoundedRect(QRectF(cx + 6 - dangle, cy + r - 2, paw_w, paw_h + 4), 6, 6)
            return

        if self.is_walking:
            # 4-Phase animated walking strides
            left_stride = math.sin(self.walk_phase * math.pi * 2) * 8.0
            right_stride = -left_stride

            painter.setBrush(QBrush(t["secondary"]))
            painter.setPen(QPen(t["accent"], 1.5))
            painter.drawRoundedRect(QRectF(cx - 22 + left_stride, cy + r - 5, paw_w, paw_h), 5, 5)
            painter.drawRoundedRect(QRectF(cx + 8 + right_stride, cy + r - 5, paw_w, paw_h), 5, 5)
        else:
            # Resting paws
            painter.setBrush(QBrush(t["secondary"]))
            painter.setPen(QPen(t["accent"], 1.5))
            painter.drawRoundedRect(QRectF(cx - 20, cy + r - 6, paw_w, paw_h), 5, 5)
            painter.drawRoundedRect(QRectF(cx + 6, cy + r - 6, paw_w, paw_h), 5, 5)

    # -----------------------------------------------------------------------
    # Face Details
    # -----------------------------------------------------------------------
    def _draw_face_details(self, painter: QPainter, cx: float, cy: float, r: float) -> None:
        t = self.theme
        avatar = self.avatar

        # 1. Blushing cheeks
        if self.state == BotState.WORKING:
            painter.setBrush(QBrush(QColor(253, 164, 175, 180)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(cx - r + 8, cy + 6), 6.0, 4.0)
            painter.drawEllipse(QPointF(cx + r - 8, cy + 6), 6.0, 4.0)

        # 2. Snout (Dog / Cat)
        if avatar == AvatarType.DOG.value:
            snout_rect = QRectF(cx - 12, cy + 2, 24, 16)
            painter.setBrush(QBrush(t["snout"]))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(snout_rect, 10, 10)

            # Dog Nose
            painter.setBrush(QBrush(QColor("#0F172A")))
            painter.drawEllipse(QPointF(cx, cy + 5), 4.5, 3.5)
            # Nose specular highlight
            painter.setBrush(QBrush(QColor("white")))
            painter.drawEllipse(QPointF(cx - 1.5, cy + 4), 1.5, 1.2)

        elif avatar == AvatarType.CAT.value:
            # Small cat nose
            painter.setBrush(QBrush(QColor("#FB7185")))
            painter.setPen(Qt.PenStyle.NoPen)
            cat_nose = QPainterPath()
            cat_nose.moveTo(cx - 3.5, cy + 4)
            cat_nose.lineTo(cx + 3.5, cy + 4)
            cat_nose.lineTo(cx, cy + 8)
            cat_nose.closeSubpath()
            painter.drawPath(cat_nose)

            # Cat Whiskers
            painter.setPen(QPen(QColor("#64748B"), 1.2))
            twitch = math.sin(self.whisker_twitch) * 2.0
            painter.drawLine(int(cx - 10), int(cy + 6), int(cx - 26), int(cy + 4 + twitch))
            painter.drawLine(int(cx - 10), int(cy + 8), int(cx - 25), int(cy + 10 - twitch))
            painter.drawLine(int(cx + 10), int(cy + 6), int(cx + 26), int(cy + 4 - twitch))
            painter.drawLine(int(cx + 10), int(cy + 8), int(cx + 25), int(cy + 10 + twitch))

        # 3. Eyes
        self._draw_eyes(painter, cx, cy, r)

        # 4. Mouth
        self._draw_mouth(painter, cx, cy, r)

    def _draw_eyes(self, painter: QPainter, cx: float, cy: float, r: float) -> None:
        eye_y = cy - 4
        avatar = self.avatar

        if self.state == BotState.SLEEPING:
            # Closed calm curved eyes
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor("#1E293B"), 2.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.drawArc(int(cx - 17), int(eye_y - 6), 12, 12, 0 * 16, 180 * 16)
            painter.drawArc(int(cx + 5), int(eye_y - 6), 12, 12, 0 * 16, 180 * 16)
            return

        if self.is_blinking:
            # Thin blink line
            painter.setPen(QPen(QColor("#1E293B"), 2.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.drawLine(int(cx - 16), int(eye_y), int(cx - 6), int(eye_y))
            painter.drawLine(int(cx + 6), int(eye_y), int(cx + 16), int(eye_y))
            return

        if avatar == AvatarType.ROBOT.value:
            # Glowing sci-fi visor / LED matrix eyes
            visor_color = QColor("#38BDF8") if self.state == BotState.WORKING else QColor("#22C55E")
            painter.setBrush(QBrush(QColor("#0F172A")))
            painter.setPen(QPen(QColor("#334155"), 1.5))
            painter.drawRoundedRect(QRectF(cx - 20, eye_y - 7, 40, 14), 4, 4)

            # LED eyes
            painter.setBrush(QBrush(visor_color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRect(QRectF(cx - 14, eye_y - 4, 8, 8))
            painter.drawRect(QRectF(cx + 6, eye_y - 4, 8, 8))
            return

        # Large shiny cartoon anime eyes
        eye_r = 5.2
        painter.setBrush(QBrush(QColor("#0F172A")))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(cx - 11, eye_y), eye_r, eye_r * 1.15)
        painter.drawEllipse(QPointF(cx + 11, eye_y), eye_r, eye_r * 1.15)

        # Primary specular highlight (big top sparkle)
        painter.setBrush(QBrush(QColor("white")))
        painter.drawEllipse(QPointF(cx - 12.5, eye_y - 2), 2.2, 2.2)
        painter.drawEllipse(QPointF(cx + 9.5, eye_y - 2), 2.2, 2.2)

        # Secondary specular highlight (small bottom sparkle)
        painter.drawEllipse(QPointF(cx - 9.5, eye_y + 2.5), 1.2, 1.2)
        painter.drawEllipse(QPointF(cx + 12.5, eye_y + 2.5), 1.2, 1.2)

    def _draw_mouth(self, painter: QPainter, cx: float, cy: float, r: float) -> None:
        mouth_y = cy + 10
        avatar = self.avatar

        # 1. Happy tongue sticking out (Working Dog)
        if self.state == BotState.WORKING and avatar == AvatarType.DOG.value:
            painter.setBrush(QBrush(QColor("#FB7185")))
            painter.setPen(QPen(QColor("#E11D48"), 1.2))
            painter.drawRoundedRect(QRectF(cx - 3.5, mouth_y + 1, 7, 8), 3, 3)

        painter.setBrush(Qt.BrushStyle.NoBrush)

        # 2. Cat "w" smile (ω)
        if avatar == AvatarType.CAT.value:
            painter.setPen(QPen(QColor("#E11D48"), 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            # Left arc of 'w'
            painter.drawArc(int(cx - 7), int(mouth_y), 7, 6, 180 * 16, 180 * 16)
            # Right arc of 'w'
            painter.drawArc(int(cx), int(mouth_y), 7, 6, 180 * 16, 180 * 16)
            return

        # 3. Dog, Robot & Smiley cheerful smile curve
        smile_pen = QPen(QColor("#E11D48"), 2.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        if avatar == AvatarType.ROBOT.value:
            smile_pen = QPen(QColor("#38BDF8"), 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)

        painter.setPen(smile_pen)

        if self.state == BotState.WORKING:
            # Extra joyful wide open smile
            painter.drawArc(int(cx - 9), int(mouth_y - 2), 18, 14, 200 * 16, 140 * 16)
        else:
            # Sweet cheerful smile by default
            painter.drawArc(int(cx - 7), int(mouth_y - 1), 14, 10, 200 * 16, 140 * 16)

    # -----------------------------------------------------------------------
    # High-Contrast Digital Timer Pill Badge
    # -----------------------------------------------------------------------
    def _draw_timer_pill(
        self,
        painter: QPainter,
        cx: float,
        cy: float,
        timer_text: str,
        timer_active: bool,
    ) -> None:
        pill_w = 114.0
        pill_h = 30.0
        pill_rect = QRectF(cx - pill_w / 2, cy, pill_w, pill_h)

        # 1. Pill Background with 32-bit glass gradient
        pill_grad = QLinearGradient(pill_rect.left(), pill_rect.top(), pill_rect.left(), pill_rect.bottom())
        pill_grad.setColorAt(0.0, QColor("#1E293B"))
        pill_grad.setColorAt(1.0, QColor("#0F172A"))

        border_color = QColor("#10B981") if timer_active else QColor("#334155")
        painter.setBrush(QBrush(pill_grad))
        painter.setPen(QPen(border_color, 1.8))
        painter.drawRoundedRect(pill_rect, 10.0, 10.0)

        # 2. Glowing Status LED Dot
        dot_color = QColor("#22C55E") if timer_active else QColor("#64748B")
        painter.setBrush(QBrush(dot_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(pill_rect.left() + 14, cy + pill_h / 2), 3.5, 3.5)

        # 3. High-Contrast Bold Digital Digits
        digit_color = QColor("#22C55E") if timer_active else QColor("#F8FAFC")
        font = QFont("Consolas", 12, QFont.Weight.Bold)
        painter.setFont(font)
        painter.setPen(digit_color)
        text_rect = QRectF(pill_rect.left() + 22, cy, pill_w - 24, pill_h)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, timer_text)
