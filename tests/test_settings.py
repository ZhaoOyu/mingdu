import json
from pathlib import Path
import tempfile
import unittest

from brightness.settings import Settings, desktop_entry


class SettingsTests(unittest.TestCase):
    def test_corrupt_settings_fall_back_and_save_round_trips(self):
        with tempfile.TemporaryDirectory() as root:
            settings = Settings(root)
            settings.path.parent.mkdir()
            settings.path.write_text("{broken")
            loaded = Settings(root)
            self.assertEqual(loaded.data["scroll_target"], "all")
            loaded.data["scroll_target"] = "ddc:8"
            loaded.save()
            self.assertEqual(Settings(root).data["scroll_target"], "ddc:8")
            self.assertEqual(json.loads(loaded.path.read_text()), {"scroll_target": "ddc:8"})

    def test_autostart_has_quoted_executable_and_removes_only_own_file(self):
        with tempfile.TemporaryDirectory() as root:
            settings = Settings(root)
            launcher = Path(root) / "my project" / "mingdu"
            settings.set_autostart(True, launcher)
            self.assertTrue(settings.autostart)
            entry = settings.autostart_path.read_text(encoding="utf-8")
            self.assertIn('Exec="', entry)
            self.assertIn('my project', entry)
            self.assertIn('" --background', entry)
            other = settings.autostart_path.parent / "other.desktop"
            other.touch()
            settings.set_autostart(False, launcher)
            self.assertFalse(settings.autostart)
            self.assertTrue(other.exists())

    def test_desktop_exec_escapes_field_codes_and_rejects_newlines(self):
        self.assertIn("100%%", desktop_entry("/tmp/100%/mingdu"))
        with self.assertRaises(ValueError):
            desktop_entry("/tmp/evil\nExec=wrong")


if __name__ == "__main__":
    unittest.main()
