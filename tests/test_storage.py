"""Tests for work_buddy.storage (SQLite storage)."""

import os
import sqlite3
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from work_buddy.models import Session, WorkLog
from work_buddy.storage import DEFAULT_DB_PATH, Storage


class TestStorage(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = Path(tempfile.mkdtemp())
        self.storage = Storage(self.tmp_dir)

    def tearDown(self):
        # Clean up temp files
        for f in self.tmp_dir.iterdir():
            f.unlink()
        self.tmp_dir.rmdir()

    def test_default_path_alongside_code(self):
        storage_default = Storage()
        self.assertEqual(storage_default.db_path, DEFAULT_DB_PATH)

    def test_load_missing_file_returns_empty(self):
        # When DB is empty/new
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
        self.assertTrue(self.storage.db_path.exists())

    def test_save_overwrites_existing(self):
        wl1 = WorkLog()
        wl1.active_session = Session(start=datetime(2026, 8, 1, 9, 0))
        self.storage.save(wl1)

        wl2 = WorkLog()
        self.storage.save(wl2)

        loaded = self.storage.load()
        self.assertIsNone(loaded.active_session)

    def test_corrupt_database_returns_empty(self):
        # Overwrite DB with corrupted non-sqlite data
        self.storage.db_path.write_text("NOT A VALID SQLITE DATABASE FILE", encoding="utf-8")

        wl = self.storage.load()
        self.assertIsNone(wl.active_session)
        self.assertEqual(len(wl.days), 0)

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
