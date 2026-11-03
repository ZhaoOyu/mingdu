from pathlib import Path
import errno
import os
import stat
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from brightness.platforms.macos import find_helper
from tools.build_macos_helpers import helper_names


class HelperPackagingTests(unittest.TestCase):
    def test_bundle_selection_with_mac_file_permissions(self):
        # Model macOS permission bits independently of the CI host filesystem.
        directory = str(Path("bundle"))
        helper = Path(directory) / "helpers/brightness"
        with patch.object(sys, "frozen", True, create=True), \
                patch.object(sys, "_MEIPASS", directory, create=True), \
                patch("brightness.platforms.macos.shutil.which", return_value="/external/brightness") as which:
            for mode, expected in (
                (stat.S_IFREG | 0o755, str(helper)),
                (stat.S_IFREG | 0o644, "/external/brightness"),
                (stat.S_IFDIR | 0o755, "/external/brightness"),
            ):
                with self.subTest(mode=oct(mode)), \
                        patch.object(Path, "stat", return_value=SimpleNamespace(st_mode=mode)):
                    which.reset_mock()
                    self.assertEqual(find_helper("brightness"), expected)
                    self.assertEqual(which.call_count, int(expected != str(helper)))
            with patch.object(Path, "stat", side_effect=FileNotFoundError(errno.ENOENT, "Missing helper")):
                self.assertEqual(find_helper("brightness"), "/external/brightness")
            which.reset_mock()
            self.assertIsNone(find_helper("../brightness"))
            which.assert_not_called()

    @unittest.skipIf(os.name == "nt", "Windows chmod does not implement Unix execute bits")
    def test_bundle_precedes_path_and_requires_executable(self):
        with tempfile.TemporaryDirectory() as directory:
            helper = Path(directory) / "helpers/brightness"
            helper.parent.mkdir()
            helper.write_text("helper")
            helper.chmod(0o755)
            with patch.object(sys, "frozen", True, create=True), patch.object(sys, "_MEIPASS", directory, create=True), \
                    patch("brightness.platforms.macos.shutil.which", return_value="/external/brightness"):
                self.assertEqual(find_helper("brightness"), str(helper))
                helper.chmod(0o644)
                self.assertEqual(find_helper("brightness"), "/external/brightness")
                self.assertIsNone(find_helper("../brightness"))

    def test_source_checkout_uses_existing_external_helper(self):
        with patch.object(sys, "frozen", False, create=True), \
                patch("brightness.platforms.macos.shutil.which", return_value="/existing/m1ddc"):
            self.assertEqual(find_helper("m1ddc"), "/existing/m1ddc")

    def test_helper_selection_matches_mac_architecture(self):
        self.assertEqual(helper_names("arm64"), ("brightness", "m1ddc"))
        self.assertEqual(helper_names("x86_64"), ("brightness", "ddcctl"))
        with self.assertRaises(ValueError):
            helper_names("unknown")
