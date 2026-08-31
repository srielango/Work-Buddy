"""Core time-tracking engine — fully independent of the GUI."""

from __future__ import annotations

import logging
from datetime import date, datetime, time, timedelta
from typing import Callable

from .models import Session, WorkLog
from .storage import Storage

logger = logging.getLogger("workbuddy")


class TimerEngine:
    """Manages work sessions, totals, midnight handling and crash recovery.

    All elapsed-time calculations are derived from real timestamps, never
    from incrementing a counter.  An injectable *clock* makes the engine
    fully testable without touching the system clock.
    """

    def __init__(
        self,
        storage: Storage,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.storage = storage
        self.clock = clock or datetime.now
        self.worklog: WorkLog = self.storage.load()
        self._recover_active_session()

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def is_working(self) -> bool:
        return self.worklog.active_session is not None

    @property
    def active_session(self) -> Session | None:
        return self.worklog.active_session

    # ------------------------------------------------------------------
    # Start / Stop
    # ------------------------------------------------------------------

    def start(self, activity: str = "") -> None:
        """Start a new work session."""
        if self.is_working:
            logger.warning("Cannot start: session already active")
            return
        now = self.clock()
        session = Session(start=now, activity=activity.strip() or None)
        self.worklog.active_session = session
        self._save()
        logger.info(
            "Session started at %s (activity: %s)",
            now.isoformat(),
            session.activity or "none",
        )

    def stop(self) -> Session | None:
        """Stop the active session and record it under the appropriate day."""
        if not self.is_working:
            logger.warning("Cannot stop: no active session")
            return None
        now = self.clock()
        session = self.worklog.active_session
        assert session is not None  # guarded above
        session.complete(now)
        day = self.worklog.get_day(session.start.date())
        day.add_session(session)
        self.worklog.active_session = None
        self._save()
        logger.info(
            "Session stopped at %s (duration: %ds)",
            now.isoformat(),
            session.duration_seconds,
        )
        return session

    # ------------------------------------------------------------------
    # Tick — called periodically by the GUI
    # ------------------------------------------------------------------

    def tick(self) -> None:
        """Called every ~500 ms.  Handles midnight crossing."""
        if self.is_working:
            self._check_midnight()

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def elapsed(self) -> timedelta:
        """Elapsed time of the current active session."""
        if not self.is_working:
            return timedelta()
        return self.worklog.active_session.elapsed(self.clock())  # type: ignore[union-attr]

    def today_total_seconds(self) -> int:
        """Total seconds worked today, including any active session."""
        now = self.clock()
        today = now.date()
        total = 0
        day = self.worklog.days.get(today.isoformat())
        if day:
            total += day.total_seconds()
        if self.is_working:
            sess = self.worklog.active_session
            assert sess is not None
            if sess.start.date() == today:
                total += int(sess.elapsed(now).total_seconds())
        return total

    def week_summary(self) -> dict[date, int]:
        """``{date: total_seconds}`` for Mon–Sun of the current week."""
        now = self.clock()
        today = now.date()
        monday = today - timedelta(days=today.weekday())
        result: dict[date, int] = {}
        for i in range(7):
            d = monday + timedelta(days=i)
            day_record = self.worklog.days.get(d.isoformat())
            total = day_record.total_seconds() if day_record else 0
            if (
                d == today
                and self.is_working
                and self.worklog.active_session  # type: ignore[union-attr]
                and self.worklog.active_session.start.date() == today
            ):
                total += int(
                    self.worklog.active_session.elapsed(now).total_seconds()
                )
            result[d] = total
        return result

    def project_summary(
        self, start_date: date, end_date: date
    ) -> dict[str, int]:
        """``{activity: total_seconds}`` for the given date range."""
        now = self.clock()
        result: dict[str, int] = {}
        current = start_date
        while current <= end_date:
            day = self.worklog.days.get(current.isoformat())
            if day:
                for s in day.sessions:
                    key = s.activity or "Unspecified"
                    result[key] = result.get(key, 0) + (s.duration_seconds or 0)
            current += timedelta(days=1)
        # Include active session if it falls within the range
        if self.is_working:
            sess = self.worklog.active_session
            assert sess is not None
            if start_date <= sess.start.date() <= end_date:
                key = sess.activity or "Unspecified"
                result[key] = result.get(key, 0) + int(
                    sess.elapsed(now).total_seconds()
                )
        return result

    def recent_activities(self) -> list[str]:
        """Most-recently-used activity names (up to 20)."""
        activities: list[str] = []
        seen: set[str] = set()
        for key in sorted(self.worklog.days.keys(), reverse=True):
            day = self.worklog.days[key]
            for session in reversed(day.sessions):
                if session.activity and session.activity not in seen:
                    activities.append(session.activity)
                    seen.add(session.activity)
                if len(activities) >= 20:
                    return activities
        return activities

    def available_months(self) -> list[tuple[int, int]]:
        """Sorted ``(year, month)`` tuples for months that have data."""
        months: set[tuple[int, int]] = set()
        for date_str in self.worklog.days:
            try:
                d = date.fromisoformat(date_str)
                months.add((d.year, d.month))
            except ValueError:
                continue
        return sorted(months)

    # ------------------------------------------------------------------
    # Midnight handling
    # ------------------------------------------------------------------

    def _check_midnight(self) -> None:
        """Close the active session at 23:59:59 if it has crossed midnight."""
        if not self.is_working:
            return
        now = self.clock()
        session = self.worklog.active_session
        assert session is not None
        if session.start.date() < now.date():
            end_of_day = datetime.combine(
                session.start.date(), time(23, 59, 59),
            )
            session.complete(end_of_day)
            day = self.worklog.get_day(session.start.date())
            day.add_session(session)
            self.worklog.active_session = None
            self._save()
            logger.info(
                "Midnight: auto-closed session from %s",
                session.start.date().isoformat(),
            )

    # ------------------------------------------------------------------
    # Crash recovery
    # ------------------------------------------------------------------

    def _recover_active_session(self) -> None:
        """On startup, handle a persisted active session."""
        if not self.is_working:
            return
        session = self.worklog.active_session
        assert session is not None
        now = self.clock()
        if session.start.date() < now.date():
            # Session from a previous day — close it at end of that day
            end_of_day = datetime.combine(
                session.start.date(), time(23, 59, 59),
            )
            session.complete(end_of_day)
            day = self.worklog.get_day(session.start.date())
            day.add_session(session)
            self.worklog.active_session = None
            self._save()
            logger.info(
                "Recovered and closed stale session from %s",
                session.start.date().isoformat(),
            )
        else:
            logger.info(
                "Recovered active session started at %s",
                session.start.isoformat(),
            )

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _save(self) -> None:
        self.storage.save(self.worklog)
