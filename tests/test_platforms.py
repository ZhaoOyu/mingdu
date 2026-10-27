import base64
from contextlib import contextmanager
import json
from pathlib import Path
import plistlib
import tempfile
import unittest
from unittest.mock import patch

from brightness.backends import Display, HardwareError
from brightness.platforms import create_hardware
from brightness.platforms.macos import MacHardware, parse_apple_brightness, parse_ddcctl_brightness, parse_ddcctl_displays, parse_m1_displays
from brightness.platforms.windows import NativeMonitor, WindowsHardware, WindowsWMI
from brightness.startup import Startup


UID = "10ACB8A0-0000-0000-1419-0104A2435078"
UID2 = "12345678-1234-1234-1234-123456789012"


class MacTests(unittest.TestCase):
    def test_m1_parser_uses_uuid_not_changeable_index(self):
        self.assertEqual(parse_m1_displays(f"[2] DELL U2723QE ({UID})\n"), [(UID, "DELL U2723QE")])
        self.assertEqual(parse_m1_displays("no supported displays"), [])

    def test_m1_range_conversion_and_readback(self):
        calls = []
        state = {"current": 128}
        def runner(args, **_kwargs):
            calls.append(args)
            if args[-2:] == ["display", "list"]:
                return f"[2] DELL ({UID})"
            if "set" in args:
                state["current"] = int(args[-1])
                return "Writing " + args[-1]
            return str(255 if "max" in args else state["current"])
        hardware = MacHardware(runner, lambda name: "/opt/homebrew/bin/m1ddc" if name == "m1ddc" else None, "arm64")
        device = hardware.discover().displays[0]
        self.assertEqual(device.value, 50)
        self.assertEqual(device.address, UID)
        self.assertEqual(hardware.set_brightness(device, 80), 80)
        self.assertIn(["/opt/homebrew/bin/m1ddc", "display", UID, "set", "luminance", "204"], calls)

    def test_m1_unreadable_device_is_not_presented_as_controllable(self):
        def runner(args, **_kwargs):
            return f"[1] Broken ({UID})" if "list" in args else "-1"
        result = MacHardware(runner, lambda name: name if name == "m1ddc" else None, "arm64").discover()
        self.assertFalse(result.displays)
        self.assertTrue(any("Broken" in warning for warning in result.warnings))

    def test_intel_parser_rejects_error_response_even_with_numbers(self):
        self.assertEqual(parse_ddcctl_brightness("I: VCP control #16 (0x10) = current: 50, max: 100"), (50, 100))
        with self.assertRaises(HardwareError):
            parse_ddcctl_brightness("E: VCP control #16 (0x10) = current: 0, max: 100")
        self.assertEqual(parse_ddcctl_displays(f"D: CGDisplay {UID} dispID(#123) (1920x1080 0°)"), [("1", UID)])

    def test_intel_re_resolves_uuid_when_index_changes(self):
        calls = []
        def runner(args, **kwargs):
            calls.append(args)
            if len(args) == 1:
                self.assertEqual(kwargs["allowed_returncodes"], (0, 1))
                return f"D: CGDisplay {UID2} dispID(#321)\nD: CGDisplay {UID} dispID(#123)"
            if args[-1] == "?":
                return "I: VCP control #16 (0x10) = current: 60, max: 100"
            return ""
        hardware = MacHardware(runner, lambda _: "ddcctl", "x86_64")
        device = Display(f"ddcctl:{UID}", "Panel", "ddcctl", UID, 100, 50)
        self.assertEqual(hardware.set_brightness(device, 60), 60)
        self.assertIn(["ddcctl", "-d", "2", "-b", "60"], calls)

    def test_apple_brightness_matches_cg_ids(self):
        output = "display 0: main, active, awake, online, built-in, ID 0xabc\ndisplay 0: brightness 0.650000\ndisplay 1: active, external, ID 0xdef\nbrightness: unable to get brightness of display 0xdef"
        devices = parse_apple_brightness(output)
        self.assertEqual(len(devices), 1)
        self.assertEqual((devices[0].address, devices[0].value), ("0xabc", 65))

    def test_missing_helpers_produces_install_hints(self):
        result = MacHardware(finder=lambda _: None, machine="arm64").discover()
        self.assertFalse(result.displays)
        self.assertTrue(any("brew install m1ddc" in message for message in result.warnings))


class FakeDDC:
    def __init__(self):
        self.released = 0
        self.current = 128
        self.fail = False
        self.present = True

    @contextmanager
    def monitors(self):
        try:
            yield ([NativeMonitor("stable-id", "DELL", 123)] if self.present else [], [])
        finally:
            self.released += 1

    def read(self, _monitor):
        if self.fail:
            raise HardwareError("disconnected")
        return self.current, 255

    def write(self, _monitor, value):
        self.current = value


class FakeWMI:
    def discover(self):
        return []


class WindowsTests(unittest.TestCase):
    def test_ddc_read_write_and_handle_scope(self):
        driver = FakeDDC()
        hardware = WindowsHardware(driver, FakeWMI())
        device = hardware.discover().displays[0]
        self.assertEqual(device.value, 50)
        self.assertEqual(hardware.set_brightness(device, 80), 80)
        self.assertEqual(driver.current, 204)
        self.assertEqual(driver.released, 2)

    def test_disconnect_does_not_reuse_stale_handle(self):
        driver = FakeDDC()
        hardware = WindowsHardware(driver, FakeWMI())
        device = hardware.discover().displays[0]
        driver.present = False
        with self.assertRaisesRegex(HardwareError, "断开"):
            hardware.set_brightness(device, 80)
        self.assertEqual(driver.released, 2)
        self.assertEqual(driver.current, 128)

    def test_failed_read_releases_handles(self):
        driver = FakeDDC()
        driver.fail = True
        result = WindowsHardware(driver, FakeWMI()).discover()
        self.assertFalse(result.displays)
        self.assertIn("disconnected", result.warnings[0])
        self.assertEqual(driver.released, 1)

    def test_wmi_single_device_array_and_encoded_command(self):
        commands = []
        def runner(args, **_kwargs):
            commands.append(args)
            return '\ufeff[{"InstanceName":"DISPLAY\\\\Panel_0","CurrentBrightness":65}]'
        wmi = WindowsWMI(runner)
        devices = wmi.discover()
        self.assertEqual(devices[0].value, 65)
        script = base64.b64decode(commands[0][-1]).decode("utf-16-le")
        self.assertIn("ConvertTo-Json -InputObject $items", script)
        self.assertIn("-NoProfile", commands[0])

    def test_wmi_interpolates_only_encoded_device_data(self):
        captured = []
        wmi = WindowsWMI(lambda args, **kwargs: captured.append(args) or "55")
        address = "DISPLAY\\Name'; Write-Host injected; '"
        device = Display("id", "Panel", "wmi", address, 100, 65)
        self.assertEqual(wmi.write(device, 55), 55)
        script = base64.b64decode(captured[0][-1]).decode("utf-16-le")
        self.assertNotIn(address, script)
        self.assertIn(base64.b64encode(address.encode()).decode(), script)
        self.assertIn("ReturnValue -ne 0", script)


class StartupAndFactoryTests(unittest.TestCase):
    def test_demo_does_not_load_platform_libraries(self):
        with patch("brightness.platforms.windows.WindowsDDC", side_effect=AssertionError("must not load")):
            self.assertEqual(len(create_hardware(demo=True, platform="win32").discover().displays), 2)

    def test_unsupported_platform_has_clear_error(self):
        with self.assertRaises(HardwareError):
            create_hardware(platform="unknown")

    def test_macos_startup_plist_preserves_arguments(self):
        with tempfile.TemporaryDirectory() as directory:
            command = ["/Applications/My App.app/Contents/MacOS/Mingdu", "--background"]
            startup = Startup("darwin", home=directory, command=command)
            startup.set_enabled(True)
            self.assertTrue(startup.enabled)
            data = plistlib.loads(startup.path.read_bytes())
            self.assertEqual(data["ProgramArguments"], command)
            self.assertTrue(data["RunAtLoad"])
            startup.set_enabled(False)
            self.assertFalse(startup.enabled)

    def test_linux_startup_preserves_python_and_script_as_separate_arguments(self):
        with tempfile.TemporaryDirectory() as directory:
            startup = Startup("linux", root=directory, command=["/tmp/my env/python", "/tmp/明度/launcher.py", "--background"])
            startup.set_enabled(True)
            content = startup.path.read_text(encoding="utf-8")
            self.assertIn('Exec="/tmp/my env/python" "/tmp/明度/launcher.py" "--background"', content)
            startup.set_enabled(False)
            self.assertFalse(startup.enabled)


if __name__ == "__main__":
    unittest.main()
