"""JSON-based persistent storage for Work Buddy."""

from __future__ import annotations

import json
import logging
import os
import tempfile
from datetime import datetime
from pathlib import Path

from .models import WorkLog

logger = logging.getLogger("workbuddy")


class Storage:
    """Manages reading and writing the worklog JSON file.

    Writes are atomic (temp-file + os.replace) so a crash mid-write
    cannot corrupt the worklog.  Corrupt files are backed up, never
    silently overwritten.
    """

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.file_path = self.data_dir / "worklog.json"

    def load(self) -> WorkLog:
        """Load the worklog from disk.

        Returns an empty WorkLog when the file is missing or corrupt.
        Corrupt files are automatically backed up.
        """
        if not self.file_path.exists():
            logger.info("No worklog file found — starting fresh")
            return WorkLog()
        try:
            text = self.file_path.read_text(encoding="utf-8")
            data = json.loads(text)
            worklog = WorkLog.from_dict(data)
            logger.info("Worklog loaded successfully")
            return worklog
        except json.JSONDecodeError as exc:
            self._backup_corrupt_file(f"JSON parse error: {exc}")
            return WorkLog()
        except (KeyError, TypeError, ValueError) as exc:
            self._backup_corrupt_file(f"Invalid data structure: {exc}")
            return WorkLog()

    def save(self, worklog: WorkLog) -> None:
        """Atomically persist the worklog to disk."""
        data = json.dumps(worklog.to_dict(), indent=2, ensure_ascii=False)
        fd, tmp_path = tempfile.mkstemp(
            dir=self.data_dir, suffix=".tmp", prefix="worklog_",
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(data)
            os.replace(tmp_path, self.file_path)
        except Exception:
            # Clean up the temp file on failure
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

    def _backup_corrupt_file(self, reason: str) -> None:
        """Rename a corrupt worklog file so it is never silently lost."""
        if self.file_path.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup = self.file_path.parent / f"worklog.corrupt.{timestamp}.json"
            self.file_path.rename(backup)
            logger.error("Corrupt worklog backed up to %s — %s", backup, reason)
        else:
            logger.error("Worklog data error (no file to back up) — %s", reason)
