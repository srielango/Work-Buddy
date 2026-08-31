"""Tests for work_buddy.storage."""

import json
import os
import tempfile
import unittest
from pathlib import Path
from datetime import datetime

from work_buddy.models import Session, WorkLog
from work_buddy.storage import Storage


class TestStorage(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = Path(tempfile.mkdtemp())
        self.storage = Storage(self.tmp_dir)

    def tearDown(self):
        # Clean up temp files
        for f in self.tmp_dir.iterdir():
            f.unlink()
        self.tmp_dir.rmdir()

    def test_load_missing_file_returns_empty(self):
        wl = self.storage.load()
        self.assertIsNone(wl.active_session)
        self.assertEqual(len(wl.days), 0)

    def test_save_and_load_roundtrip(self):
        wl = WorkLog()
        wl.active_session = Session(
            start=datetime(2026, 8, 31, 9, 0), activity="Test",
        )
        self.storage.save(wl)

        wl2 = self.storage.load()
        self.assertIsNotNone(wl2.active_session)
        self.assertEqual(wl2.active_session.start, datetime(2026, 8, 31, 9, 0))
        self.assertEqual(wl2.active_session.activity, "Test")

    def test_save_creates_file(self):
        self.storage.save(WorkLog())
        self.assertTrue(self.storage.file_path.exists())

    def test_save_overwrites_existing(self):
        wl1 = WorkLog()
        wl1.active_session = Session(start=datetime(2026, 8, 1, 9, 0))
        self.storage.save(wl1)

        wl2 = WorkLog()
        self.storage.save(wl2)

        loaded = self.storage.load()
        self.assertIsNone(loaded.active_session)

    def test_corrupt_json_returns_empty_and_backs_up(self):
        self.storage.file_path.write_text("NOT VALID JSON!!!", encoding="utf-8")

        wl = self.storage.load()
        self.assertIsNone(wl.active_session)
        self.assertEqual(len(wl.days), 0)

        # Original file should be renamed
        self.assertFalse(self.storage.file_path.exists())
        # Backup should exist
        backups = list(self.tmp_dir.glob("worklog.corrupt.*.json"))
        self.assertEqual(len(backups), 1)

    def test_invalid_structure_returns_empty_and_backs_up(self):
        # Valid JSON but invalid structure
        data = {"active_session": {"not_a_real_field": 42}}
        self.storage.file_path.write_text(json.dumps(data), encoding="utf-8")

        wl = self.storage.load()
        self.assertIsNone(wl.active_session)

        backups = list(self.tmp_dir.glob("worklog.corrupt.*.json"))
        self.assertEqual(len(backups), 1)

    def test_atomic_write_leaves_no_temp_files(self):
        self.storage.save(WorkLog())
        temps = list(self.tmp_dir.glob("worklog_*.tmp"))
        self.assertEqual(len(temps), 0)

    def test_multiple_saves_preserve_data(self):
        wl = WorkLog()
        day = wl.get_day(datetime(2026, 8, 31).date())
        s1 = Session(
            start=datetime(2026, 8, 31, 9, 0),
            end=datetime(2026, 8, 31, 10, 0),
            duration_seconds=3600,
        )
        day.add_session(s1)
        self.storage.save(wl)

        # Add another session and save again
        s2 = Session(
            start=datetime(2026, 8, 31, 11, 0),
            end=datetime(2026, 8, 31, 12, 0),
            duration_seconds=3600,
        )
        day.add_session(s2)
        self.storage.save(wl)

        loaded = self.storage.load()
        self.assertEqual(len(loaded.days["2026-08-31"].sessions), 2)


if __name__ == "__main__":
    unittest.main()
