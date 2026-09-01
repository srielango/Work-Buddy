"""PyQt6 Desktop Pet Companion Window for Work Buddy."""

from __future__ import annotations

import logging
import math
import random
from datetime import datetime
from pathlib import Path
from PyQt6.QtCore import QPoint, QRectF, QSize, Qt, QTimer
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QIcon,
    QMouseEvent,
    QPainter,
    QPen,
)
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .autostart import set_autostart
from .export_dialog_qt import ExportDialogQt
from .models import AvatarType, BotState, ColorTheme, format_duration, format_timer
from .pet_painter import PetPainter
from .settings import Settings
from .summary_window_qt import SummaryWindowQt
from .timer_engine import TimerEngine

logger = logging.getLogger("workbuddy")


class PetWindow(QWidget):
    """The always-on-top transparent animated desktop pet companion."""

    COLLAPSED_W = 150
    COLLAPSED_H = 135
    EXPANDED_W = 260
    EXPANDED_H = 440

    def __init__(
        self,
        engine: TimerEngine,
        settings: Settings,
        data_dir: Path,
    ) -> None:
        super().__init__()
        self.engine = engine
        self.settings = settings
        self.data_dir = data_dir
        self.expanded = False

        # Pet painter & state
        self.painter_engine = PetPainter()
        self.painter_engine.avatar = self.settings.avatar
        self.painter_engine.theme_name = self.settings.theme

        # Drag state
        self._drag_start_pos: QPoint | None = None
        self._is_dragging = False

        # Walking physics state
        self._walk_direction = 0  # -1 for left, 0 for idle, 1 for right
        self._walk_timer_countdown = 0.0
        self._idle_since: datetime | None = (
            None if engine.is_working else datetime.now()
        )

        # Restore dot window
        self._restore_dot: QWidget | None = None

        self._setup_window()
        self._setup_tummy_widgets()
        self._setup_timers()
        self._update_display()

    # -----------------------------------------------------------------------
    # Window Setup
    # -----------------------------------------------------------------------
    def _setup_window(self) -> None:
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.SubWindow
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(self.COLLAPSED_W, self.COLLAPSED_H)

        # Position window
        screen = QApplication.primaryScreen().geometry()
        if self.settings.bot_x is not None and self.settings.bot_y is not None:
            self.move(self.settings.bot_x, self.settings.bot_y)
        else:
            self.move(
                screen.width() - self.COLLAPSED_W - 60,
                screen.height() - self.COLLAPSED_H - 120,
            )

    # -----------------------------------------------------------------------
    # Tummy Panel Widgets (Expanded Mode)
    # -----------------------------------------------------------------------
    def _setup_tummy_widgets(self) -> None:
        """Create controls embedded in the character's belly."""
        self.tummy_container = QWidget(self)
        self.tummy_container.setGeometry(28, 92, 204, 310)
        self.tummy_container.setStyleSheet("""
            QWidget {
                background-color: transparent;
                font-family: 'Segoe UI', sans-serif;
            }
            QLabel {
                color: #1E293B;
            }
            QComboBox {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                padding: 3px 6px;
                font-size: 11px;
                color: #0F172A;
            }
            QPushButton.toggle-start {
                background-color: #16A34A;
                color: #FFFFFF;
                font-weight: bold;
                font-size: 12px;
                border: none;
                border-radius: 8px;
                padding: 6px 12px;
            }
            QPushButton.toggle-start:hover {
                background-color: #22C55E;
            }
            QPushButton.toggle-stop {
                background-color: #DC2626;
                color: #FFFFFF;
                font-weight: bold;
                font-size: 12px;
                border: none;
                border-radius: 8px;
                padding: 6px 12px;
            }
            QPushButton.toggle-stop:hover {
                background-color: #EF4444;
            }
            QPushButton.avatar-btn {
                background-color: #FEF3C7;
                border: 1px solid #FCD34D;
                border-radius: 6px;
                font-size: 14px;
                padding: 2px;
            }
            QPushButton.avatar-btn:hover {
                background-color: #FDE68A;
            }
            QPushButton.theme-btn {
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                font-size: 10px;
                padding: 2px 4px;
            }
            QPushButton.icon-tool {
                background-color: #FEF3C7;
                border: 1px solid #FDE68A;
                border-radius: 6px;
                font-size: 11px;
                padding: 3px 6px;
            }
            QPushButton.icon-tool:hover {
                background-color: #FDE68A;
            }
        """)

        layout = QVBoxLayout(self.tummy_container)
        layout.setContentsMargins(4, 2, 4, 4)
        layout.setSpacing(4)

        # Status Label
        self.status_label = QLabel("● READY")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.status_label.setStyleSheet("color: #64748B;")
        layout.addWidget(self.status_label)

        # LCD Timer Display Badge
        lcd_frame = QFrame()
        lcd_frame.setStyleSheet("""
            background-color: #0F172A;
            border: 1px solid #334155;
            border-radius: 8px;
            padding: 3px 8px;
        """)
        lcd_layout = QHBoxLayout(lcd_frame)
        lcd_layout.setContentsMargins(0, 0, 0, 0)
        self.lcd_label = QLabel("00:00:00")
        self.lcd_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lcd_label.setFont(QFont("Consolas", 15, QFont.Weight.Bold))
        self.lcd_label.setStyleSheet("color: #F8FAFC; border: none;")
        lcd_layout.addWidget(self.lcd_label)
        layout.addWidget(lcd_frame)

        # Activity Field
        self.activity_combo = QComboBox()
        self.activity_combo.setEditable(True)
        self.activity_combo.addItems(self.engine.recent_activities())
        layout.addWidget(self.activity_combo)

        # Start / Stop Belly Button
        self.toggle_btn = QPushButton("▶ START")
        self.toggle_btn.setProperty("class", "toggle-start")
        self.toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_btn.clicked.connect(self._toggle_work)
        layout.addWidget(self.toggle_btn)

        # Today's Total
        self.today_label = QLabel("Today: 0h 00m")
        self.today_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.today_label.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.today_label.setStyleSheet("color: #1E293B;")
        layout.addWidget(self.today_label)

        # Avatar Switcher Row (🐶 🐱 🤖 😊)
        avatar_row = QHBoxLayout()
        avatar_row.setSpacing(4)
        avatars = [
            (AvatarType.DOG.value, "🐶"),
            (AvatarType.CAT.value, "🐱"),
            (AvatarType.ROBOT.value, "🤖"),
            (AvatarType.SMILEY.value, "😊"),
        ]
        for atype, icon in avatars:
            btn = QPushButton(icon)
            btn.setProperty("class", "avatar-btn")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, a=atype: self._set_avatar(a))
            avatar_row.addWidget(btn)
        layout.addLayout(avatar_row)

        # Theme Color Switcher Row
        theme_row = QHBoxLayout()
        theme_row.setSpacing(2)
        themes = [
            (ColorTheme.GOLDEN.value, "🟡"),
            (ColorTheme.SNOW.value, "⚪"),
            (ColorTheme.CHOCOLATE.value, "🟤"),
            (ColorTheme.MIDNIGHT.value, "🖤"),
            (ColorTheme.SAKURA.value, "🌸"),
            (ColorTheme.CYBER.value, "🟢"),
        ]
        for tname, icon in themes:
            btn = QPushButton(icon)
            btn.setProperty("class", "theme-btn")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, t=tname: self._set_theme(t))
            theme_row.addWidget(btn)
        layout.addLayout(theme_row)

        # Accessory Toolbar Row (📊 📋 🐾 ─ ✕)
        toolbar = QHBoxLayout()
        toolbar.setSpacing(3)

        btn_sum = QPushButton("📊")
        btn_sum.setProperty("class", "icon-tool")
        btn_sum.setToolTip("Weekly Summary")
        btn_sum.clicked.connect(self._show_summary)
        toolbar.addWidget(btn_sum)

        btn_exp = QPushButton("📋")
        btn_exp.setProperty("class", "icon-tool")
        btn_exp.setToolTip("Export to Excel")
        btn_exp.clicked.connect(self._export_excel)
        toolbar.addWidget(btn_exp)

        self.btn_walk = QPushButton("🚶" if self.settings.walking_enabled else "🛑")
        self.btn_walk.setProperty("class", "icon-tool")
        self.btn_walk.setToolTip("Toggle Desktop Walking")
        self.btn_walk.clicked.connect(self._toggle_walking)
        toolbar.addWidget(self.btn_walk)

        self.btn_autostart = QPushButton("🚀" if self.settings.start_with_windows else "💤")
        self.btn_autostart.setProperty("class", "icon-tool")
        self.btn_autostart.setToolTip(
            "Start with Windows: " + ("ON (Starts on logon)" if self.settings.start_with_windows else "OFF")
        )
        self.btn_autostart.clicked.connect(self._toggle_autostart)
        toolbar.addWidget(self.btn_autostart)

        btn_min = QPushButton("─")
        btn_min.setProperty("class", "icon-tool")
        btn_min.setToolTip("Minimize")
        btn_min.clicked.connect(self._minimize)
        toolbar.addWidget(btn_min)

        btn_exit = QPushButton("✕")
        btn_exit.setProperty("class", "icon-tool")
        btn_exit.setToolTip("Exit")
        btn_exit.clicked.connect(self.on_exit)
        toolbar.addWidget(btn_exit)

        layout.addLayout(toolbar)

        # Hide tummy container when collapsed
        self.tummy_container.setVisible(False)

    # -----------------------------------------------------------------------
    # Timers (60 FPS Animation & Engine Tick)
    # -----------------------------------------------------------------------
    def _setup_timers(self) -> None:
        # 60 FPS animation timer (16ms)
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self._animation_tick)
        self.anim_timer.start(16)

        # 500ms time-tracking engine tick
        self.engine_timer = QTimer(self)
        self.engine_timer.timeout.connect(self._update_display)
        self.engine_timer.start(500)

        # Blink timer
        self._blink_timer = QTimer(self)
        self._blink_timer.setSingleShot(True)
        self._blink_timer.timeout.connect(self._do_blink)
        self._schedule_blink()

    def _schedule_blink(self) -> None:
        lo, hi = (2500, 5000) if self.engine.is_working else (3500, 7000)
        self._blink_timer.start(random.randint(lo, hi))

    def _do_blink(self) -> None:
        self.painter_engine.is_blinking = True
        self.update()
        QTimer.singleShot(140, self._end_blink)

    def _end_blink(self) -> None:
        self.painter_engine.is_blinking = False
        self.update()
        self._schedule_blink()

    # -----------------------------------------------------------------------
    # 60 FPS Animation & Walking Physics Loop
    # -----------------------------------------------------------------------
    def _animation_tick(self) -> None:
        dt = 0.016
        pe = self.painter_engine
        pe.particles.update(dt)

        # Tail wag animation
        pe.tail_phase += dt * (10.0 if self.engine.is_working else 4.0)

        # Whisker twitch for kitty
        pe.whisker_twitch += dt * 3.0

        # Walking physics (collapsed mode only)
        if (
            not self.expanded
            and not self._is_dragging
            and self.settings.walking_enabled
            and pe.state != BotState.SLEEPING
        ):
            self._update_walking_physics(dt)
        else:
            pe.is_walking = False
            pe.bounce_y = 0.0

        # Sleeping Zzz particle spawn
        if pe.state == BotState.SLEEPING and random.random() < 0.02:
            pe.particles.spawn_zzz(self.width() / 2, 40)

        self.update()

    def _update_walking_physics(self, dt: float) -> None:
        pe = self.painter_engine
        self._walk_timer_countdown -= dt

        if self._walk_timer_countdown <= 0:
            # Pick a new behavior: walk left, walk right, or rest
            choice = random.choice(["left", "right", "idle", "idle"])
            if choice == "left":
                self._walk_direction = -1
                self._walk_timer_countdown = random.uniform(2.0, 5.0)
            elif choice == "right":
                self._walk_direction = 1
                self._walk_timer_countdown = random.uniform(2.0, 5.0)
            else:
                self._walk_direction = 0
                self._walk_timer_countdown = random.uniform(3.0, 7.0)

        if self._walk_direction != 0:
            pe.is_walking = True
            pe.facing_left = (self._walk_direction < 0)
            pe.walk_phase += dt * 3.5
            pe.bounce_y = math.sin(pe.walk_phase * math.pi * 2) * 2.5

            speed = 1.2
            dx = int(self._walk_direction * speed)
            new_x = self.x() + dx

            # Screen bounds check
            screen = QApplication.primaryScreen().geometry()
            if new_x < 10:
                new_x = 10
                self._walk_direction = 1
            elif new_x > screen.width() - self.width() - 10:
                new_x = screen.width() - self.width() - 10
                self._walk_direction = -1

            self.move(new_x, self.y())
        else:
            pe.is_walking = False
            pe.bounce_y = 0.0

    # -----------------------------------------------------------------------
    # Paint Event
    # -----------------------------------------------------------------------
    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        cx = self.width() / 2.0
        cy = 44.0

        timer_str = "00:00:00"
        active = False
        if self.engine.is_working:
            elapsed = self.engine.elapsed()
            timer_str = format_timer(int(elapsed.total_seconds()))
            active = True

        self.painter_engine.draw_pet(
            painter,
            cx=cx,
            cy=cy,
            radius=32.0,
            is_expanded=self.expanded,
            timer_text=timer_str,
            timer_active=active,
        )

    # -----------------------------------------------------------------------
    # Mouse Interaction (Petting, Dragging, Expand/Collapse)
    # -----------------------------------------------------------------------
    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = event.globalPosition().toPoint() - self.pos()
            self._is_dragging = False
            # Playful petting: spawn floating heart/sparkle particles!
            self.painter_engine.particles.spawn_heart(event.position().x(), event.position().y())

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag_start_pos is not None:
            delta = (event.globalPosition().toPoint() - self.pos()) - self._drag_start_pos
            if delta.manhattanLength() > 6:
                self._is_dragging = True
                self.painter_engine.is_held = True
                self.move(event.globalPosition().toPoint() - self._drag_start_pos)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.painter_engine.is_held = False
            if self._is_dragging:
                self._is_dragging = False
                self.settings.bot_x = self.x()
                self.settings.bot_y = self.y()
            else:
                # Click on head toggles expand/collapse
                if not self.expanded or event.position().y() <= 85:
                    self._toggle_expand()
            self._drag_start_pos = None

    # -----------------------------------------------------------------------
    # Expand / Collapse
    # -----------------------------------------------------------------------
    def _toggle_expand(self) -> None:
        if self.expanded:
            self._collapse()
        else:
            self._expand()

    def _expand(self) -> None:
        self.expanded = True
        self.setFixedSize(self.EXPANDED_W, self.EXPANDED_H)
        self.tummy_container.setVisible(True)
        self._refresh_activity_list()
        self._sync_expanded_labels()
        self.update()

    def _collapse(self) -> None:
        self.expanded = False
        self.tummy_container.setVisible(False)
        self.setFixedSize(self.COLLAPSED_W, self.COLLAPSED_H)
        self.update()

    # -----------------------------------------------------------------------
    # Avatar, Theme & Walking Settings
    # -----------------------------------------------------------------------
    def _set_avatar(self, avatar_name: str) -> None:
        self.painter_engine.avatar = avatar_name
        self.settings.avatar = avatar_name
        self.settings.save(self.data_dir / "settings.json")
        self.painter_engine.particles.spawn_heart(self.width() / 2, 40)
        self.update()

    def _set_theme(self, theme_name: str) -> None:
        self.painter_engine.theme_name = theme_name
        self.settings.theme = theme_name
        self.settings.save(self.data_dir / "settings.json")
        self.update()

    def _toggle_walking(self) -> None:
        self.settings.walking_enabled = not self.settings.walking_enabled
        self.btn_walk.setText("🚶" if self.settings.walking_enabled else "🛑")
        self.settings.save(self.data_dir / "settings.json")

    def _toggle_autostart(self) -> None:
        self.settings.start_with_windows = not self.settings.start_with_windows
        set_autostart(self.settings.start_with_windows)
        self.btn_autostart.setText("🚀" if self.settings.start_with_windows else "💤")
        self.btn_autostart.setToolTip(
            "Start with Windows: " + ("ON (Starts on logon)" if self.settings.start_with_windows else "OFF")
        )
        self.settings.save(self.data_dir / "settings.json")
        self.painter_engine.particles.spawn_heart(self.width() / 2, 40)
        self.update()

    # -----------------------------------------------------------------------
    # Start / Stop Toggle
    # -----------------------------------------------------------------------
    def _toggle_work(self) -> None:
        if self.engine.is_working:
            self.engine.stop()
            self._idle_since = datetime.now()
        else:
            act = self.activity_combo.currentText().strip()
            self.engine.start(act)
            self._idle_since = None
            self.painter_engine.particles.spawn_heart(self.width() / 2, 40)

        self._sync_expanded_labels()
        self._sync_bot_visual()
        self.update()

    def _refresh_activity_list(self) -> None:
        current = self.activity_combo.currentText()
        self.activity_combo.clear()
        self.activity_combo.addItems(self.engine.recent_activities())
        if current:
            self.activity_combo.setCurrentText(current)

    def _sync_expanded_labels(self) -> None:
        if self.engine.is_working:
            self.status_label.setText("● WORKING")
            self.status_label.setStyleSheet("color: #16A34A; font-weight: bold;")
            self.lcd_label.setStyleSheet("color: #22C55E; border: none;")
            self.toggle_btn.setText("⏹ STOP")
            self.toggle_btn.setStyleSheet("""
                background-color: #DC2626; color: white; font-weight: bold;
                border-radius: 8px; padding: 6px;
            """)
            sess = self.engine.active_session
            if sess and sess.activity:
                self.activity_combo.setCurrentText(sess.activity)
        else:
            self.status_label.setText("● READY")
            self.status_label.setStyleSheet("color: #64748B; font-weight: bold;")
            self.lcd_label.setStyleSheet("color: #F8FAFC; border: none;")
            self.toggle_btn.setText("▶ START")
            self.toggle_btn.setStyleSheet("""
                background-color: #16A34A; color: white; font-weight: bold;
                border-radius: 8px; padding: 6px;
            """)

    # -----------------------------------------------------------------------
    # 500ms Display Update
    # -----------------------------------------------------------------------
    def _update_display(self) -> None:
        try:
            self.engine.tick()

            timer_str = "00:00:00"
            if self.engine.is_working:
                elapsed = self.engine.elapsed()
                timer_str = format_timer(int(elapsed.total_seconds()))

            if self.expanded:
                self.lcd_label.setText(timer_str)
                total = self.engine.today_total_seconds()
                self.today_label.setText(f"Today: {format_duration(total)}")
                self._sync_expanded_labels()

            self._sync_bot_visual()
        except Exception:
            logger.exception("Error in display update")

    def _sync_bot_visual(self) -> None:
        if self.engine.is_working:
            self.painter_engine.state = BotState.WORKING
            self._idle_since = None
            return

        if self._idle_since is None:
            self._idle_since = datetime.now()

        idle_min = (datetime.now() - self._idle_since).total_seconds() / 60
        if idle_min >= self.settings.sleep_minutes:
            self.painter_engine.state = BotState.SLEEPING
        elif idle_min >= self.settings.idle_minutes:
            self.painter_engine.state = BotState.IDLE
        else:
            self.painter_engine.state = BotState.STOPPED

    # -----------------------------------------------------------------------
    # Dialogs & Windows
    # -----------------------------------------------------------------------
    def _show_summary(self) -> None:
        dlg = SummaryWindowQt(self, self.engine)
        dlg.exec()

    def _export_excel(self) -> None:
        months = self.engine.available_months()
        if not months:
            QMessageBox.information(self, "Export", "No data to export yet.")
            return
        dlg = ExportDialogQt(self, self.engine, months)
        dlg.exec()

    def _minimize(self) -> None:
        if self.expanded:
            self._collapse()
        self.hide()
        self._create_restore_dot()

    def _create_restore_dot(self) -> None:
        dot = QWidget()
        dot.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.SubWindow
        )
        dot.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        dot.setFixedSize(44, 44)
        dot.move(self.x(), self.y())

        def paint_dot(e):
            p = QPainter(dot)
            p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            t = self.painter_engine.theme
            p.setBrush(QBrush(t["primary"]))
            p.setPen(QPen(t["secondary"], 2.0))
            p.drawEllipse(2, 2, 40, 40)
            p.setBrush(QBrush(QColor("#1E293B")))
            p.drawEllipse(14, 16, 4, 4)
            p.drawEllipse(26, 16, 4, 4)

        dot.paintEvent = paint_dot
        dot.mousePressEvent = lambda e: self._restore_from_dot(dot)
        dot.show()
        self._restore_dot = dot

    def _restore_from_dot(self, dot: QWidget) -> None:
        dot.close()
        self._restore_dot = None
        self.show()

    def on_exit(self) -> None:
        if self.engine.is_working:
            res = QMessageBox.question(
                self,
                "Work Buddy",
                "A work session is currently active.\nExit anyway? (Session will be saved and recovered on next start)",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if res != QMessageBox.StandardButton.Yes:
                return

        self.settings.bot_x = self.x()
        self.settings.bot_y = self.y()
        self.settings.save(self.data_dir / "settings.json")
        self.engine.storage.save(self.engine.worklog)
        logger.info("Work Buddy exiting")

        if self._restore_dot:
            self._restore_dot.close()
        QApplication.quit()
