"""Application orchestrator for Work Buddy."""

from __future__ import annotations

import logging
import os
import tkinter as tk
from pathlib import Path

from .bot_window import BotWindow
from .logging_config import setup_logging
from .settings import Settings
from .storage import Storage
from .timer_engine import TimerEngine

logger = logging.getLogger("workbuddy")


class WorkBuddyApp:
    """Top-level class that wires Storage, TimerEngine, Settings and the GUI."""

    def __init__(self) -> None:
        self.data_dir = self._get_data_dir()
        self.data_dir.mkdir(parents=True, exist_ok=True)

        setup_logging(self.data_dir)
        logger.info("Work Buddy starting")

        self.settings = Settings.load(self.data_dir / "settings.json")
        self.storage = Storage(self.data_dir)
        self.engine = TimerEngine(self.storage)

        # Create root but keep it hidden until BotWindow configures it
        self.root = tk.Tk()
        self.root.withdraw()

        self.bot_window = BotWindow(
            self.root, self.engine, self.settings, self.data_dir,
        )

        # Show the fully-configured window
        self.root.deiconify()

    def run(self) -> None:
        """Enter the Tkinter main loop."""
        logger.info("Work Buddy ready")
        self.root.mainloop()

    @staticmethod
    def _get_data_dir() -> Path:
        """Determine the data directory (%LOCALAPPDATA%/WorkBuddy or ~/.workbuddy)."""
        local = os.environ.get("LOCALAPPDATA")
        if local:
            return Path(local) / "WorkBuddy"
        return Path.home() / ".workbuddy"
