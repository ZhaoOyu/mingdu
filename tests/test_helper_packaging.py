from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from brightness.platforms.macos import find_helper
from tools.build_macos_helpers import helper_names


class HelperPackagingTests(unittest.TestCase):
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
