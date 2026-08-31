"""Application settings for Work Buddy."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path

logger = logging.getLogger("workbuddy")


@dataclass
class Settings:
    """Persisted user-configurable settings."""

    always_on_top: bool = True
    animations_enabled: bool = True
    idle_minutes: int = 15
    sleep_minutes: int = 30
    bot_x: int | None = None
    bot_y: int | None = None
    avatar: str = "dog"
    theme: str = "golden"
    walking_enabled: bool = True

    def save(self, path: Path) -> None:
        """Write settings to a JSON file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> Settings:
        """Load settings from JSON, returning defaults on any error."""
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            known = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
            return cls(**known)
        except (FileNotFoundError, json.JSONDecodeError, TypeError) as exc:
            logger.info("Using default settings (%s)", exc)
            return cls()
