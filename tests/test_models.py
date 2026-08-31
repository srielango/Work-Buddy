"""Tests for work_buddy.models."""

import unittest
from datetime import datetime, timedelta, date

from work_buddy.models import (
    BotState,
    DayRecord,
    Session,
    WorkLog,
    format_duration,
    format_timer,
)


class TestSession(unittest.TestCase):
    def test_new_session_is_active(self):
        s = Session(start=datetime(2026, 8, 31, 9, 0))
        self.assertTrue(s.is_active)
        self.assertIsNone(s.end)
        self.assertIsNone(s.duration_seconds)

    def test_complete_marks_session_done(self):
        s = Session(start=datetime(2026, 8, 31, 9, 0))
        s.complete(datetime(2026, 8, 31, 11, 30))
        self.assertFalse(s.is_active)
        self.assertEqual(s.duration_seconds, 9000)  # 2.5 hours
        self.assertEqual(s.end, datetime(2026, 8, 31, 11, 30))

    def test_elapsed_active_session(self):
        s = Session(start=datetime(2026, 8, 31, 9, 0))
        now = datetime(2026, 8, 31, 10, 30)
        self.assertEqual(s.elapsed(now), timedelta(hours=1, minutes=30))

    def test_elapsed_completed_session(self):
        s = Session(start=datetime(2026, 8, 31, 9, 0))
        s.complete(datetime(2026, 8, 31, 11, 0))
        # elapsed should use stored duration regardless of `now`
        self.assertEqual(s.elapsed(datetime(2026, 12, 1)), timedelta(hours=2))

    def test_complete_prevents_negative_duration(self):
        s = Session(start=datetime(2026, 8, 31, 10, 0))
        s.complete(datetime(2026, 8, 31, 9, 0))  # end before start
        self.assertEqual(s.duration_seconds, 0)

    def test_serialization_roundtrip(self):
        s = Session(
            start=datetime(2026, 8, 31, 9, 10),
            end=datetime(2026, 8, 31, 11, 40),
            duration_seconds=9000,
            activity="Trading Bot",
        )
        d = s.to_dict()
        s2 = Session.from_dict(d)
        self.assertEqual(s2.start, s.start)
        self.assertEqual(s2.end, s.end)
        self.assertEqual(s2.duration_seconds, s.duration_seconds)
        self.assertEqual(s2.activity, s.activity)

    def test_serialization_active_session(self):
        s = Session(start=datetime(2026, 8, 31, 14, 0), activity="Coding")
        d = s.to_dict()
        self.assertNotIn("end", d)
        self.assertNotIn("duration_seconds", d)
        s2 = Session.from_dict(d)
        self.assertTrue(s2.is_active)
        self.assertEqual(s2.activity, "Coding")

    def test_serialization_no_activity(self):
        s = Session(start=datetime(2026, 8, 31, 9, 0))
        d = s.to_dict()
        self.assertNotIn("activity", d)


class TestDayRecord(unittest.TestCase):
    def test_empty_day_has_zero_total(self):
        day = DayRecord(date=date(2026, 8, 31))
        self.assertEqual(day.total_seconds(), 0)

    def test_total_seconds_sums_completed(self):
        day = DayRecord(date=date(2026, 8, 31))
        s1 = Session(
            start=datetime(2026, 8, 31, 9, 0),
            end=datetime(2026, 8, 31, 10, 0),
            duration_seconds=3600,
        )
        s2 = Session(
            start=datetime(2026, 8, 31, 11, 0),
            end=datetime(2026, 8, 31, 12, 30),
            duration_seconds=5400,
        )
        day.add_session(s1)
        day.add_session(s2)
        self.assertEqual(day.total_seconds(), 9000)

    def test_total_seconds_ignores_active(self):
        day = DayRecord(date=date(2026, 8, 31))
        completed = Session(
            start=datetime(2026, 8, 31, 9, 0),
            end=datetime(2026, 8, 31, 10, 0),
            duration_seconds=3600,
        )
        active = Session(start=datetime(2026, 8, 31, 14, 0))
        day.add_session(completed)
        day.add_session(active)
        self.assertEqual(day.total_seconds(), 3600)

    def test_serialization_roundtrip(self):
        day = DayRecord(date=date(2026, 8, 31))
        day.add_session(Session(
            start=datetime(2026, 8, 31, 9, 0),
            end=datetime(2026, 8, 31, 10, 0),
            duration_seconds=3600,
            activity="Research",
        ))
        d = day.to_dict()
        day2 = DayRecord.from_dict("2026-08-31", d)
        self.assertEqual(day2.date, day.date)
        self.assertEqual(len(day2.sessions), 1)
        self.assertEqual(day2.sessions[0].activity, "Research")


class TestWorkLog(unittest.TestCase):
    def test_empty_worklog(self):
        wl = WorkLog()
        self.assertIsNone(wl.active_session)
        self.assertEqual(len(wl.days), 0)

    def test_get_day_creates_on_demand(self):
        wl = WorkLog()
        day = wl.get_day(date(2026, 8, 31))
        self.assertIsNotNone(day)
        self.assertEqual(day.date, date(2026, 8, 31))
        self.assertIn("2026-08-31", wl.days)

    def test_get_day_returns_existing(self):
        wl = WorkLog()
        day1 = wl.get_day(date(2026, 8, 31))
        day2 = wl.get_day(date(2026, 8, 31))
        self.assertIs(day1, day2)

    def test_full_roundtrip(self):
        wl = WorkLog()
        wl.active_session = Session(
            start=datetime(2026, 8, 31, 14, 0), activity="Trading Bot",
        )
        day = wl.get_day(date(2026, 8, 31))
        day.add_session(Session(
            start=datetime(2026, 8, 31, 9, 0),
            end=datetime(2026, 8, 31, 11, 30),
            duration_seconds=9000,
            activity="Trading Bot",
        ))
        d = wl.to_dict()
        wl2 = WorkLog.from_dict(d)
        self.assertIsNotNone(wl2.active_session)
        self.assertEqual(wl2.active_session.activity, "Trading Bot")
        self.assertIn("2026-08-31", wl2.days)
        self.assertEqual(wl2.days["2026-08-31"].total_seconds(), 9000)

    def test_from_dict_without_active_session(self):
        data = {"days": {}}
        wl = WorkLog.from_dict(data)
        self.assertIsNone(wl.active_session)

    def test_from_dict_with_null_active_session(self):
        data = {"days": {}, "active_session": None}
        wl = WorkLog.from_dict(data)
        self.assertIsNone(wl.active_session)


class TestFormatDuration(unittest.TestCase):
    def test_zero(self):
        self.assertEqual(format_duration(0), "0h 00m")

    def test_minutes_only(self):
        self.assertEqual(format_duration(37 * 60), "0h 37m")

    def test_hours_and_minutes(self):
        self.assertEqual(format_duration(4 * 3600 + 37 * 60), "4h 37m")

    def test_many_hours(self):
        self.assertEqual(format_duration(100 * 3600), "100h 00m")


class TestFormatTimer(unittest.TestCase):
    def test_zero(self):
        self.assertEqual(format_timer(0), "00:00:00")

    def test_typical(self):
        self.assertEqual(format_timer(3600 + 42 * 60 + 35), "01:42:35")

    def test_negative_clamped(self):
        self.assertEqual(format_timer(-10), "00:00:00")


if __name__ == "__main__":
    unittest.main()
