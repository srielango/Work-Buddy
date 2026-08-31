"""Tests for work_buddy.timer_engine."""

import tempfile
import unittest
from datetime import date, datetime, time, timedelta
from pathlib import Path

from work_buddy.models import Session, WorkLog
from work_buddy.storage import Storage
from work_buddy.timer_engine import TimerEngine


class _ClockHelper:
    """Injectable clock for deterministic tests."""

    def __init__(self, initial: datetime) -> None:
        self._now = initial

    def __call__(self) -> datetime:
        return self._now

    def advance(self, **kwargs) -> None:
        self._now += timedelta(**kwargs)

    def set(self, dt: datetime) -> None:
        self._now = dt


def _make_engine(
    clock: _ClockHelper | None = None,
    tmp_dir: Path | None = None,
) -> tuple[TimerEngine, Storage, _ClockHelper]:
    """Create a TimerEngine with a temp directory and injectable clock."""
    if tmp_dir is None:
        tmp_dir = Path(tempfile.mkdtemp())
    if clock is None:
        clock = _ClockHelper(datetime(2026, 8, 31, 9, 0, 0))
    storage = Storage(tmp_dir)
    engine = TimerEngine(storage, clock=clock)
    return engine, storage, clock


class TestStartStop(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.engine, self.storage, self.clock = _make_engine(tmp_dir=self.tmp)

    def tearDown(self):
        for f in self.tmp.iterdir():
            f.unlink()
        self.tmp.rmdir()

    def test_start_creates_active_session(self):
        self.engine.start("Trading Bot")
        self.assertTrue(self.engine.is_working)
        self.assertEqual(self.engine.active_session.activity, "Trading Bot")
        self.assertEqual(
            self.engine.active_session.start, datetime(2026, 8, 31, 9, 0, 0),
        )

    def test_start_without_activity(self):
        self.engine.start()
        self.assertTrue(self.engine.is_working)
        self.assertIsNone(self.engine.active_session.activity)

    def test_start_strips_whitespace_activity(self):
        self.engine.start("  ")
        self.assertIsNone(self.engine.active_session.activity)

    def test_double_start_is_noop(self):
        self.engine.start("A")
        self.engine.start("B")
        self.assertEqual(self.engine.active_session.activity, "A")

    def test_stop_records_session(self):
        self.engine.start("Coding")
        self.clock.advance(hours=2, minutes=30)
        session = self.engine.stop()

        self.assertFalse(self.engine.is_working)
        self.assertIsNotNone(session)
        self.assertEqual(session.duration_seconds, 9000)
        self.assertEqual(session.activity, "Coding")

    def test_stop_while_not_working_returns_none(self):
        result = self.engine.stop()
        self.assertIsNone(result)

    def test_session_persisted_on_start(self):
        self.engine.start("Test")
        # Reload from disk
        engine2 = TimerEngine(self.storage, clock=self.clock)
        self.assertTrue(engine2.is_working)
        self.assertEqual(engine2.active_session.activity, "Test")

    def test_session_cleared_on_stop(self):
        self.engine.start()
        self.clock.advance(minutes=30)
        self.engine.stop()
        engine2 = TimerEngine(self.storage, clock=self.clock)
        self.assertFalse(engine2.is_working)


class TestElapsedAndTotals(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.engine, _, self.clock = _make_engine(tmp_dir=self.tmp)

    def tearDown(self):
        for f in self.tmp.iterdir():
            f.unlink()
        self.tmp.rmdir()

    def test_elapsed_while_working(self):
        self.engine.start()
        self.clock.advance(hours=1, minutes=42, seconds=35)
        elapsed = self.engine.elapsed()
        self.assertEqual(int(elapsed.total_seconds()), 6155)

    def test_elapsed_while_stopped(self):
        self.assertEqual(self.engine.elapsed(), timedelta())

    def test_today_total_single_session(self):
        self.engine.start()
        self.clock.advance(hours=2)
        self.engine.stop()
        self.assertEqual(self.engine.today_total_seconds(), 7200)

    def test_today_total_multiple_sessions(self):
        # Session 1: 9:00 - 11:00
        self.engine.start()
        self.clock.advance(hours=2)
        self.engine.stop()

        # Session 2: 12:00 - 13:30
        self.clock.advance(hours=1)  # now 12:00
        self.engine.start()
        self.clock.advance(hours=1, minutes=30)
        self.engine.stop()

        self.assertEqual(
            self.engine.today_total_seconds(),
            7200 + 5400,  # 2h + 1h30m
        )

    def test_today_total_includes_active_session(self):
        # Completed: 1 hour
        self.engine.start()
        self.clock.advance(hours=1)
        self.engine.stop()

        # Active: 30 minutes so far
        self.clock.advance(hours=1)
        self.engine.start()
        self.clock.advance(minutes=30)

        total = self.engine.today_total_seconds()
        self.assertEqual(total, 3600 + 1800)

    def test_today_total_no_sessions(self):
        self.assertEqual(self.engine.today_total_seconds(), 0)


class TestWeekSummary(unittest.TestCase):
    def test_week_summary_shows_full_week(self):
        # Aug 31, 2026 is a Monday
        clock = _ClockHelper(datetime(2026, 8, 31, 9, 0))
        tmp = Path(tempfile.mkdtemp())
        engine, _, _ = _make_engine(clock=clock, tmp_dir=tmp)

        engine.start("Work")
        clock.advance(hours=6, minutes=40)
        engine.stop()

        summary = engine.week_summary()
        self.assertEqual(len(summary), 7)

        monday = date(2026, 8, 31)
        self.assertEqual(summary[monday], 6 * 3600 + 40 * 60)

        # Other days should be 0
        for d, secs in summary.items():
            if d != monday:
                self.assertEqual(secs, 0)

        for f in tmp.iterdir():
            f.unlink()
        tmp.rmdir()


class TestProjectSummary(unittest.TestCase):
    def test_groups_by_activity(self):
        clock = _ClockHelper(datetime(2026, 8, 31, 9, 0))
        tmp = Path(tempfile.mkdtemp())
        engine, _, _ = _make_engine(clock=clock, tmp_dir=tmp)

        engine.start("Trading Bot")
        clock.advance(hours=2)
        engine.stop()

        clock.advance(minutes=15)
        engine.start("Python Learning")
        clock.advance(hours=1)
        engine.stop()

        clock.advance(minutes=15)
        engine.start("Trading Bot")
        clock.advance(hours=1)
        engine.stop()

        projects = engine.project_summary(date(2026, 8, 31), date(2026, 8, 31))
        self.assertEqual(projects["Trading Bot"], 10800)  # 3h
        self.assertEqual(projects["Python Learning"], 3600)  # 1h

        for f in tmp.iterdir():
            f.unlink()
        tmp.rmdir()

    def test_unspecified_activity(self):
        clock = _ClockHelper(datetime(2026, 8, 31, 9, 0))
        tmp = Path(tempfile.mkdtemp())
        engine, _, _ = _make_engine(clock=clock, tmp_dir=tmp)

        engine.start()  # no activity
        clock.advance(hours=1)
        engine.stop()

        projects = engine.project_summary(date(2026, 8, 31), date(2026, 8, 31))
        self.assertIn("Unspecified", projects)
        self.assertEqual(projects["Unspecified"], 3600)

        for f in tmp.iterdir():
            f.unlink()
        tmp.rmdir()


class TestRecentActivities(unittest.TestCase):
    def test_returns_recent_first(self):
        clock = _ClockHelper(datetime(2026, 8, 31, 9, 0))
        tmp = Path(tempfile.mkdtemp())
        engine, _, _ = _make_engine(clock=clock, tmp_dir=tmp)

        for name in ["Alpha", "Beta", "Gamma"]:
            engine.start(name)
            clock.advance(hours=1)
            engine.stop()
            clock.advance(minutes=15)

        activities = engine.recent_activities()
        self.assertEqual(activities, ["Gamma", "Beta", "Alpha"])

        for f in tmp.iterdir():
            f.unlink()
        tmp.rmdir()

    def test_deduplicates(self):
        clock = _ClockHelper(datetime(2026, 8, 31, 9, 0))
        tmp = Path(tempfile.mkdtemp())
        engine, _, _ = _make_engine(clock=clock, tmp_dir=tmp)

        for name in ["A", "B", "A"]:
            engine.start(name)
            clock.advance(hours=1)
            engine.stop()
            clock.advance(minutes=15)

        activities = engine.recent_activities()
        self.assertEqual(activities, ["A", "B"])

        for f in tmp.iterdir():
            f.unlink()
        tmp.rmdir()


class TestMidnight(unittest.TestCase):
    def test_midnight_closes_session(self):
        clock = _ClockHelper(datetime(2026, 8, 31, 23, 30))
        tmp = Path(tempfile.mkdtemp())
        engine, _, _ = _make_engine(clock=clock, tmp_dir=tmp)

        engine.start("Late Night")
        # Advance past midnight
        clock.advance(hours=1)  # now 2026-09-01 00:30
        engine.tick()

        self.assertFalse(engine.is_working)
        day = engine.worklog.days.get("2026-08-31")
        self.assertIsNotNone(day)
        self.assertEqual(len(day.sessions), 1)
        self.assertEqual(
            day.sessions[0].end,
            datetime(2026, 8, 31, 23, 59, 59),
        )

        for f in tmp.iterdir():
            f.unlink()
        tmp.rmdir()

    def test_midnight_does_not_auto_start_next_day(self):
        clock = _ClockHelper(datetime(2026, 8, 31, 23, 30))
        tmp = Path(tempfile.mkdtemp())
        engine, _, _ = _make_engine(clock=clock, tmp_dir=tmp)

        engine.start()
        clock.advance(hours=1)
        engine.tick()

        self.assertFalse(engine.is_working)
        self.assertNotIn("2026-09-01", engine.worklog.days)

        for f in tmp.iterdir():
            f.unlink()
        tmp.rmdir()


class TestRecovery(unittest.TestCase):
    def test_recover_same_day_session(self):
        clock = _ClockHelper(datetime(2026, 8, 31, 9, 0))
        tmp = Path(tempfile.mkdtemp())
        engine, storage, _ = _make_engine(clock=clock, tmp_dir=tmp)

        engine.start("Recovery Test")
        clock.advance(hours=2)

        # Simulate restart: create new engine at 11:00
        engine2 = TimerEngine(storage, clock=clock)
        self.assertTrue(engine2.is_working)
        self.assertEqual(engine2.active_session.activity, "Recovery Test")
        elapsed = engine2.elapsed()
        self.assertEqual(int(elapsed.total_seconds()), 7200)

        for f in tmp.iterdir():
            f.unlink()
        tmp.rmdir()

    def test_recover_stale_session_from_previous_day(self):
        clock = _ClockHelper(datetime(2026, 8, 31, 22, 0))
        tmp = Path(tempfile.mkdtemp())
        engine, storage, _ = _make_engine(clock=clock, tmp_dir=tmp)

        engine.start("Overnight")
        # App crashes; restart next day at 08:00
        clock.set(datetime(2026, 9, 1, 8, 0))
        engine2 = TimerEngine(storage, clock=clock)

        self.assertFalse(engine2.is_working)
        day = engine2.worklog.days.get("2026-08-31")
        self.assertIsNotNone(day)
        self.assertEqual(len(day.sessions), 1)
        self.assertEqual(
            day.sessions[0].end,
            datetime(2026, 8, 31, 23, 59, 59),
        )

        for f in tmp.iterdir():
            f.unlink()
        tmp.rmdir()

    def test_recover_no_active_session(self):
        clock = _ClockHelper(datetime(2026, 8, 31, 9, 0))
        tmp = Path(tempfile.mkdtemp())
        engine, storage, _ = _make_engine(clock=clock, tmp_dir=tmp)

        # No session started — restart should be fine
        engine2 = TimerEngine(storage, clock=clock)
        self.assertFalse(engine2.is_working)

        for f in tmp.iterdir():
            f.unlink()
        tmp.rmdir()


class TestAvailableMonths(unittest.TestCase):
    def test_returns_sorted_months(self):
        clock = _ClockHelper(datetime(2026, 9, 15, 9, 0))
        tmp = Path(tempfile.mkdtemp())
        engine, _, _ = _make_engine(clock=clock, tmp_dir=tmp)

        # Create data across two months
        clock.set(datetime(2026, 8, 15, 9, 0))
        engine.start()
        clock.advance(hours=1)
        engine.stop()

        clock.set(datetime(2026, 9, 1, 9, 0))
        engine.start()
        clock.advance(hours=1)
        engine.stop()

        months = engine.available_months()
        self.assertEqual(months, [(2026, 8), (2026, 9)])

        for f in tmp.iterdir():
            f.unlink()
        tmp.rmdir()


if __name__ == "__main__":
    unittest.main()
