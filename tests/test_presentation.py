from types import SimpleNamespace
import unittest

from brightness.presentation import brightness_summary


class BrightnessPresentationTests(unittest.TestCase):
    def setUp(self):
        self.displays = {"a": SimpleNamespace(name="内置屏幕"), "b": SimpleNamespace(name="外接屏幕")}

    def test_no_monitors_or_incomplete_reading_has_no_numeric_claim(self):
        for displays, confirmed in [({}, {}), (self.displays, {"a": 65})]:
            with self.subTest(displays=displays):
                summary = brightness_summary(displays, confirmed)
                self.assertIsNone(summary.value)
                self.assertEqual(summary.text, "--")

    def test_mixed_brightness_does_not_show_an_average(self):
        summary = brightness_summary(self.displays, {"a": 20, "b": 80})
        self.assertIsNone(summary.value)
        self.assertEqual(summary.text, "≠")

    def test_selected_screen_has_its_own_confirmed_value(self):
        summary = brightness_summary(self.displays, {"a": 20, "b": 80}, "b")
        self.assertEqual((summary.value, summary.text), (80, "80"))
        self.assertIn("外接屏幕", summary.description)

    def test_equal_brightness_and_boundary_values(self):
        for value in (0, 1, 65, 100):
            summary = brightness_summary(self.displays, {"a": value, "b": value})
            self.assertEqual(summary.value, value)
            self.assertEqual(summary.text, str(value))

    def test_failed_screen_is_visible_but_does_not_mask_healthy_selection(self):
        values, errors = {"a": 25, "b": 25}, {"a": "disconnected"}
        self.assertEqual(brightness_summary(self.displays, values, errors=errors).text, "!")
        self.assertEqual(brightness_summary(self.displays, values, "a", errors).text, "!")
        self.assertEqual(brightness_summary(self.displays, values, "b", errors).value, 25)

    def test_removed_selection_falls_back_to_available_displays(self):
        summary = brightness_summary(self.displays, {"a": 60, "b": 60}, "removed")
        self.assertEqual(summary.value, 60)
