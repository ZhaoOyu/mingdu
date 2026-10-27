from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from brightness.backends import Display, Hardware, HardwareError, parse_detect, parse_vcp, percent, raw_value, run_command


DETECTION = """Display 1
   I2C bus: /dev/i2c-7
   Monitor: DEL:DELL U2723QE:AB123

Invalid display
   I2C bus: /dev/i2c-9
   Monitor: ABC:Unsupported:123

Display 2
   I2C bus: /dev/i2c-12
   Monitor: ACR:Acer X243W:567
"""


class BackendTests(unittest.TestCase):
    def test_detect_ignores_invalid_and_phantom_displays(self):
        self.assertEqual(parse_detect(DETECTION), [("7", "DELL U2723QE"), ("12", "Acer X243W")])
        self.assertEqual(parse_detect("No displays found"), [])
        self.assertEqual(parse_detect("Phantom display\n I2C bus: /dev/i2c-3"), [])

    def test_detect_does_not_assume_usb_has_i2c_bus(self):
        self.assertEqual(parse_detect("Display 1\n USB bus: 001\n Monitor: USB:Panel:1"), [])

    def test_vcp_parsing_uses_decimal_range(self):
        self.assertEqual(parse_vcp("notice\nVCP 10 C 128 255\n"), (128, 255))
        self.assertEqual(percent(128, 255), 50)
        self.assertEqual(raw_value(50, 255), 128)

    def test_bad_or_unsupported_ranges_are_rejected(self):
        for output in ["VCP 10 ERR", "VCP 10 C 1 0", "VCP 10 C 120 100", "VCP 12 C 50 100"]:
            with self.subTest(output=output), self.assertRaises(HardwareError):
                parse_vcp(output)
        for value in (0, -5, 101):
            with self.assertRaises(ValueError):
                raw_value(value, 100)
        self.assertEqual(raw_value(1, 10), 1)
        self.assertEqual(percent(0, 100), 0)

    def test_discovery_isolates_monitor_failure_and_reads_backlight(self):
        calls = []
        def run(args, **kwargs):
            calls.append(args)
            if "detect" in args:
                return DETECTION
            if "7" in args:
                return "VCP 10 C 128 255"
            raise HardwareError("permission denied")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            device = root / "intel_backlight"
            device.mkdir()
            (device / "max_brightness").write_text("2000\n")
            (device / "brightness").write_text("800\n")
            result = Hardware(run, root, which=lambda _: "/usr/bin/ddcutil").discover()
        self.assertEqual([d.value for d in result.displays], [40, 50])
        self.assertTrue(any("permission denied" in message for message in result.warnings))
        self.assertEqual(len(calls), 3)

    def test_missing_ddcutil_is_actionable(self):
        with tempfile.TemporaryDirectory() as directory:
            result = Hardware(backlight_root=directory, which=lambda _: None).discover()
        self.assertEqual(result.displays, [])
        self.assertIn("sudo apt install ddcutil", result.warnings[0])

    def test_set_commands_use_raw_brightness_and_argument_arrays(self):
        calls = []
        hardware = Hardware(runner=lambda args: calls.append(args))
        ddc = Display("ddc:7", "DELL", "ddc", "7", 255, 20)
        self.assertEqual(hardware.set_brightness(ddc, 50), 50)
        self.assertEqual(calls.pop(), ["ddcutil", "--bus", "7", "setvcp", "10", "128"])
        internal = Display("b:panel", "Panel", "backlight", "intel_backlight", 4000, 50)
        hardware.set_brightness(internal, 25)
        command = calls.pop()
        self.assertIn("/org/freedesktop/login1/session/auto", command)
        self.assertEqual(command[-3:], ["backlight", "intel_backlight", "1000"])

    def test_command_timeout_and_errors_are_reported(self):
        with patch("brightness.backends.subprocess.run", side_effect=subprocess.TimeoutExpired("ddcutil", 12)):
            with self.assertRaisesRegex(HardwareError, "超时"):
                run_command(["ddcutil"])
        result = subprocess.CompletedProcess(["ddcutil"], 1, "", "Permission denied")
        with patch("brightness.backends.subprocess.run", return_value=result) as call:
            with self.assertRaisesRegex(HardwareError, "Permission denied"):
                run_command(["ddcutil", "detect"])
            self.assertEqual(call.call_args.kwargs["env"]["LC_ALL"], "C")
            self.assertNotIn("shell", call.call_args.kwargs)


if __name__ == "__main__":
    unittest.main()
