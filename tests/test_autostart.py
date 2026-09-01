"""Tests for Windows autostart module."""

import sys
import unittest
from unittest.mock import MagicMock, patch

from work_buddy import autostart


class TestAutostart(unittest.TestCase):
    def test_get_launch_command_contains_main_or_exe(self):
        cmd = autostart._get_launch_command()
        self.assertTrue(len(cmd) > 0)
        self.assertTrue("main.py" in cmd or ".exe" in cmd)

    @patch("sys.platform", "win32")
    def test_set_autostart_enable_and_disable(self):
        # Test enabling
        res_enable = autostart.set_autostart(True)
        self.assertTrue(res_enable)
        self.assertTrue(autostart.is_autostart_enabled())

        # Test disabling
        res_disable = autostart.set_autostart(False)
        self.assertTrue(res_disable)
        self.assertFalse(autostart.is_autostart_enabled())

    @patch("sys.platform", "linux")
    def test_autostart_non_windows_graceful(self):
        self.assertFalse(autostart.is_autostart_enabled())
        self.assertFalse(autostart.set_autostart(True))


if __name__ == "__main__":
    unittest.main()
