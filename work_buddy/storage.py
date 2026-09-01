"""SQLite-based persistent storage for Work Buddy."""

from __future__ import annotations

import contextlib
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Iterator

from .models import DayRecord, Session, WorkLog

logger = logging.getLogger("workbuddy")

# Default database stored alongside the codebase
DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "workbuddy.db"


class Storage:
    """Manages reading and writing work sessions to an SQLite database table."""

    def __init__(self, db_path: Path | str | None = None) -> None:
        if db_path is None:
            self.db_path = DEFAULT_DB_PATH
        else:
            p = Path(db_path)
            if p.is_dir() or p.suffix == "":
                self.db_path = p / "workbuddy.db"
            else:
                self.db_path = p
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @property
    def file_path(self) -> Path:
        """Alias for db_path for backwards compatibility."""
        return self.db_path

    @contextlib.contextmanager
    def _get_connection(self) -> Iterator[sqlite3.Connection]:
        """Context manager that yields a database connection and ensures it is closed."""
        conn = sqlite3.connect(str(self.db_path))
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self) -> None:
        """Initialize the SQLite database schema if not already present."""
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    start TEXT NOT NULL,
                    end TEXT,
                    duration_seconds INTEGER,
                    activity TEXT,
                    is_active INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            conn.commit()

    def load(self) -> WorkLog:
        """Load all sessions from the SQLite database and construct a WorkLog."""
        if not self.db_path.exists():
            logger.info("No database found — starting fresh")
            return WorkLog()

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT start, end, duration_seconds, activity, is_active
                    FROM sessions
                    ORDER BY start ASC, id ASC
                    """
                )
                rows = cursor.fetchall()

            active_session: Session | None = None
            days: dict[str, DayRecord] = {}

            for start_str, end_str, duration_seconds, activity, is_active in rows:
                start_dt = datetime.fromisoformat(start_str)
                end_dt = datetime.fromisoformat(end_str) if end_str else None

                session = Session(
                    start=start_dt,
                    end=end_dt,
                    duration_seconds=duration_seconds,
                    activity=activity,
                )

                if is_active or (end_dt is None and active_session is None):
                    active_session = session
                else:
                    date_key = start_dt.date().isoformat()
                    if date_key not in days:
                        days[date_key] = DayRecord(date=start_dt.date())
                    days[date_key].add_session(session)

            logger.info("Worklog loaded successfully from SQLite DB (%s)", self.db_path)
            return WorkLog(active_session=active_session, days=days)

        except Exception as exc:
            logger.error("Failed to load worklog from database: %s", exc)
            return WorkLog()

    def save(self, worklog: WorkLog) -> None:
        """Persist the worklog to the SQLite database."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM sessions")

                # Insert completed sessions organized by day
                for day_rec in worklog.days.values():
                    for session in day_rec.sessions:
                        cursor.execute(
                            """
                            INSERT INTO sessions (start, end, duration_seconds, activity, is_active)
                            VALUES (?, ?, ?, ?, 0)
                            """,
                            (
                                session.start.isoformat(),
                                session.end.isoformat() if session.end else None,
                                session.duration_seconds,
                                session.activity,
                            ),
                        )

                # Insert active session if present
                if worklog.active_session:
                    s = worklog.active_session
                    cursor.execute(
                        """
                        INSERT INTO sessions (start, end, duration_seconds, activity, is_active)
                        VALUES (?, ?, ?, ?, 1)
                        """,
                        (
                            s.start.isoformat(),
                            s.end.isoformat() if s.end else None,
                            s.duration_seconds,
                            s.activity,
                        ),
                    )
                conn.commit()
            logger.info("Worklog saved successfully to SQLite DB (%s)", self.db_path)
        except Exception as exc:
            logger.error("Failed to save worklog to database: %s", exc)
            raise
