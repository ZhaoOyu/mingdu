# Validation / 验证记录

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
