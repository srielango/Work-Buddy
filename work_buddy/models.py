"""Data models for Work Buddy."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from enum import Enum


class BotState(Enum):
    """Visual state of the bot companion."""

    WORKING = "working"
    STOPPED = "stopped"
    IDLE = "idle"
    SLEEPING = "sleeping"


@dataclass
class Session:
    """A single work session."""

    start: datetime
    end: datetime | None = None
    duration_seconds: int | None = None
    activity: str | None = None

    @property
    def is_active(self) -> bool:
        return self.end is None

    def elapsed(self, now: datetime | None = None) -> timedelta:
        """Calculate elapsed time. Uses *now* for active sessions."""
        if self.end is not None:
            return timedelta(seconds=self.duration_seconds or 0)
        now = now or datetime.now()
        return now - self.start

    def complete(self, end_time: datetime) -> None:
        """Mark the session as completed at *end_time*."""
        self.end = end_time
        self.duration_seconds = max(0, int((end_time - self.start).total_seconds()))

    # -- Serialisation --

    def to_dict(self) -> dict:
        d: dict = {"start": self.start.isoformat()}
        if self.end is not None:
            d["end"] = self.end.isoformat()
        if self.duration_seconds is not None:
            d["duration_seconds"] = self.duration_seconds
        if self.activity:
            d["activity"] = self.activity
        return d

    @classmethod
    def from_dict(cls, data: dict) -> Session:
        return cls(
            start=datetime.fromisoformat(data["start"]),
            end=datetime.fromisoformat(data["end"]) if "end" in data else None,
            duration_seconds=data.get("duration_seconds"),
            activity=data.get("activity"),
        )


@dataclass
class DayRecord:
    """All work sessions for a single calendar day."""

    date: date
    sessions: list[Session] = field(default_factory=list)

    def total_seconds(self) -> int:
        """Total completed work seconds for this day."""
        return sum(s.duration_seconds or 0 for s in self.sessions if not s.is_active)

    def add_session(self, session: Session) -> None:
        self.sessions.append(session)

    def to_dict(self) -> dict:
        return {"sessions": [s.to_dict() for s in self.sessions]}

    @classmethod
    def from_dict(cls, date_str: str, data: dict) -> DayRecord:
        return cls(
            date=date.fromisoformat(date_str),
            sessions=[Session.from_dict(s) for s in data.get("sessions", [])],
        )


@dataclass
class WorkLog:
    """Complete work log — optional active session + historical day records."""

    active_session: Session | None = None
    days: dict[str, DayRecord] = field(default_factory=dict)

    def get_day(self, d: date) -> DayRecord:
        """Get or create a DayRecord for the given date."""
        key = d.isoformat()
        if key not in self.days:
            self.days[key] = DayRecord(date=d)
        return self.days[key]

    def to_dict(self) -> dict:
        result: dict = {"days": {k: v.to_dict() for k, v in self.days.items()}}
        if self.active_session:
            result["active_session"] = self.active_session.to_dict()
        return result

    @classmethod
    def from_dict(cls, data: dict) -> WorkLog:
        active = None
        if data.get("active_session"):
            active = Session.from_dict(data["active_session"])
        days = {}
        for date_str, day_data in data.get("days", {}).items():
            days[date_str] = DayRecord.from_dict(date_str, day_data)
        return cls(active_session=active, days=days)


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def format_duration(total_seconds: int) -> str:
    """Format seconds as 'Xh YYm' (e.g. '4h 37m')."""
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    return f"{hours}h {minutes:02d}m"


def format_timer(total_seconds: int) -> str:
    """Format seconds as 'HH:MM:SS' for the live timer."""
    total_seconds = max(0, total_seconds)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
