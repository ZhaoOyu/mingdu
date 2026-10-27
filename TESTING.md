# Validation / 验证记录

## 1.1 development · 2026-10-27

Local environment: Ubuntu 26.04, Python 3.14. Qt tests use an offscreen renderer and simulated displays. No physical monitor writes were performed.

- 31 unit tests (one native ABI check runs only on Windows): Linux parsing/range/error/queue/config behavior; Windows handle scopes, disconnects, range conversion, WMI encoding and ctypes layouts; macOS helper parsing, UUID selection, changed Intel display order, readback and missing helpers; platform selection and startup files.
- Real Qt widget integration: slider debounce, QAction tray commands, individual scrolling, multi-monitor presets, failure rollback, stale result suppression, refresh ordering, empty state and demo mode.
- Two-process tests validate single-instance activation both from source and from the frozen application, with temporary user configuration and simulated displays.
- GitHub Actions is configured for Ubuntu, Windows, macOS arm64 and Intel tests/native packaging, plus GTK compatibility. Check the actual workflow run before describing a remote job as passed.

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
