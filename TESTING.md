# Validation / 验证记录

## Sun-ring indicator · 2026-11-03

- Shared 296-degree upper arc with a bottom sun, central brightness digits and unchanged confirmed-value semantics. AppKit uses the native `sun.max.fill` symbol; Qt and GTK render matching shapes.
- AppKit/Qt widget integration, native process activation, and Ubuntu GTK integration passed with simulated hardware. GTK symbolic recoloring retains the progress opacity, numerals and bottom sun. 46 unit tests ran with one Windows-only skip; Ruff passed.

## Native AppKit frontend · 2026-11-03

- macOS defaults to AppKit; the frozen Mac app excludes Qt. The popup is an actual `NSPopover` with a native `NSPopoverFrame`, system visual-effect material, SF Symbols, NSSlider, NSButton, NSPopUpButton and NSButton checkbox controls.
- 46 unit tests ran (one Windows-only ABI test skipped), Ruff passed. AppKit widget integration passed with simulated hardware: read-only startup, debounced input, confirmed tray values, per-screen selection, presets, rollback and empty-state diagnostics. Source and frozen two-process activation passed.
- Both Aqua and Dark Aqua popovers rendered successfully, 340×488 logical content size for two displays. Native component previews are exported using AppKit's view cache; the compositor's background blur and window shadow are not reproduced by that export.
- The frozen app's helper architecture, licenses and source hashes passed. Its read-only hardware diagnostic still recognized the Apple backlight and Kuycon G27-X using bundled tools with a system-only PATH. No physical brightness writes were made for this UI iteration.
- The arm64 DMG passed `hdiutil verify`. Native desktop automation could not read this accessory app's popup (timeout); AppKit's own widget/render tests and live process startup were used. Intel Mac runtime remains unverified.

## Local macOS hardware and bundled helpers · 2026-11-03

- macOS arm64: 42 unit tests ran, one Windows-only ABI test skipped; Ruff passed. Native bundle build succeeded with pinned `brightness` and `m1ddc` executables, license notices and exact source archives. Finder version metadata reads 1.1.0 instead of the previous 0.0.0.
- Packaged `Mingdu --diagnose` with PATH restricted to `/usr/bin:/bin:/usr/sbin:/sbin` found the Apple backlight screen and Kuycon G27-X at 100%. Neither helper was installed in Homebrew. An additional `Unknown Display` candidate could not be controlled and remained a diagnostic warning.
- Explicit, local-only hardware test clicked each real screen's minus button in the new Qt panel: 100% → 95%, confirmed by a fresh device read. The other screen remained at 100%; the selected tray ring showed 95. Each tested screen was then restored and independently read back at 100%.
- Physical writes are not part of CI. The one-off local test used the binaries from the frozen app with the source UI and restored the initial values. The frozen application's diagnostic and two-process startup checks passed separately.
- Intel helper selection is unit-tested; Intel compilation/runtime and other monitors still require CI or actual hardware verification. The older Homebrew on this Mac could not recognize macOS 26.6; no Homebrew update or system-wide helper installation was performed.

## Unreleased UI · 2026-11-03

- macOS arm64, Python 3.13 and PySide6 6.12: Ruff passed; 39 unit tests ran, with the Windows-only ABI test skipped. Qt integration and two-process single-instance checks passed.
- Native Cocoa rendering checked in light/dark modes at 380 logical pixels wide. Combo popup, preset click, Escape dismissal and tray reopening passed with simulated displays. Secondary text uses a blended system color, preserving contrast when the platform palette supplies alpha colors.
- Ubuntu 22.04 arm64 VM: GTK/Xvfb integration passed, including read-only startup, confirmed tray values, mixed brightness, errors and preset state. GTK's actual symbolic loader retained the hollow ring, outlined digits and progress opacity. Light/dark GTK rendering checked at 380 pixels wide; deb build and Cairo/SVG dependency metadata checked.
- Preview images use simulated devices. One GTK preview export via `Gdk.pixbuf_get_from_window` hit a Cairo assertion in Xvfb; exporting through `Gtk.Widget.draw` succeeded. The GTK interaction smoke test's screenshot path passed.
- No physical display brightness was changed. Windows native UI, GNOME/Wayland tray placement, and new frozen installers were not tested in this UI iteration. These changes have not been released.

## 1.1.0 Preview 1 · 2026-10-27

Local environment: Ubuntu 26.04, Python 3.14. Qt tests use an offscreen renderer and simulated displays. No physical monitor writes were performed.

- 33 unit tests (one native ABI check runs only on Windows): Linux parsing/range/error/queue/config behavior; Windows handle scopes, disconnects, range conversion, WMI encoding and ctypes layouts; macOS helper parsing, UUID selection, changed Intel display order, readback and missing helpers; platform selection and startup files.
- Real Qt widget integration: slider debounce, QAction tray commands, individual scrolling, multi-monitor presets, failure rollback, stale result suppression, refresh ordering, empty state and demo mode.
- Two-process tests validate single-instance activation both from source and from the frozen application, with temporary user configuration and simulated displays.
- [Release workflow 40464867767](https://github.com/ZhaoOyu/mingdu/actions/runs/40464867767) passed on Ubuntu 22.04, Windows 2025, macOS 15 arm64 and macOS 15 Intel, with a separate Ubuntu GTK compatibility job.
- Windows installer: silent per-user installation, installed-app two-process startup and uninstallation passed. Both macOS DMGs passed hdiutil verification.
- Release assembly tests reject missing, duplicate and empty packages and mismatched version tags. Published all six packages, INSTALL.md and SHA256SUMS.txt; the checksum manifest matches GitHub asset digests.
- Published [v1.1.0-preview.1](https://github.com/ZhaoOyu/mingdu/releases/tag/v1.1.0-preview.1) from commit `1183fb6741a10055ef5fc12ce98a802fb4ef7e2e`. Binaries are not trusted-signed or Apple-notarized.

## 1.0 baseline · 2026-10-23

Ubuntu GTK passed 14 unit tests and an Xvfb integration test with GTK critical warnings treated as fatal. User install/uninstall, desktop-entry validation and deb permissions were checked. No real monitor was available.

## Manual hardware validation still required

Record application version/commit, OS, architecture, helper version, monitor model and connection. Use ordinary working brightness values and restore the original setting after testing.

| Platform | Required checks |
|---|---|
| Ubuntu | logind laptop; HDMI/DP ddcutil; GNOME tray menu/wheel; login startup |
| Windows | x64 DXVA2 external panel; WMI laptop; tray; HKCU startup; disconnect during writes |
| macOS arm64 | brightness built-in panel; m1ddc USB-C/DP/supported HDMI; menu bar; LaunchAgent |
| macOS Intel | ddcctl/brightness; display reordering; menu bar; LaunchAgent |

Also verify multi-monitor independence, non-100 raw maximums, wake followed by Refresh, unsupported DDC, disconnected cables and permission errors. There is no polling or automatic restore.

An installer is not hardware certification. Hosted CI normally has no physical DDC monitors. Keep packaging/UI results separate from compatibility claims.
