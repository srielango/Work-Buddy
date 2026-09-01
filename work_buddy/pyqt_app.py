"""Application orchestrator for Work Buddy PyQt6 Desktop Companion."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication

from .autostart import set_autostart
from .logging_config import setup_logging
from .pet_window import PetWindow
from .settings import Settings
from .storage import Storage
from .timer_engine import TimerEngine

logger = logging.getLogger("workbuddy")


class WorkBuddyAppQt:
    """Orchestrator for the PyQt6 Desktop Companion."""

    def __init__(self) -> None:
        self.data_dir = self._get_data_dir()
        self.data_dir.mkdir(parents=True, exist_ok=True)

        setup_logging(self.data_dir)
        logger.info("Work Buddy (PyQt6 Desktop Companion) starting")

        self.settings = Settings.load(self.data_dir / "settings.json")
        self.storage = Storage(self.data_dir)
        self.engine = TimerEngine(self.storage)

        # Sync autostart registry setting
        if self.settings.start_with_windows:
            set_autostart(True)

        # Qt Application
        self.qapp = QApplication.instance() or QApplication(sys.argv)
        self.qapp.setApplicationName("Work Buddy")

        self.window = PetWindow(
            self.engine, self.settings, self.data_dir
        )
        self.window.show()

    def run(self) -> None:
        """Enter the Qt event loop."""
        logger.info("Work Buddy Desktop Companion ready")
        sys.exit(self.qapp.exec())

    @staticmethod
    def _get_data_dir() -> Path:
        """Determine data directory (%LOCALAPPDATA%/WorkBuddy or ~/.workbuddy)."""
        local = os.environ.get("LOCALAPPDATA")
        if local:
            return Path(local) / "WorkBuddy"
        return Path.home() / ".workbuddy"
