# Changelog

## 1.2.0 — 2026-11-03 (Preview 1)

- Brightness indicators now use an upper progress arc, central number and bottom sun across macOS, Qt and GTK.
- Updated Chinese/English download and installation guides for the new preview.
- Cross-platform helper tests model macOS permission bits while retaining real Unix permission checks.

- macOS now defaults to a real AppKit NSPopover with system material, SF Symbols, native sliders/buttons and light/dark appearance; the Mac bundle no longer contains Qt.
- AppKit hardware controller preserves debounce, confirmed-value rings, read-only startup and failure rollback; repeated launches activate the existing native panel.

- macOS bundles include architecture-specific brightness helpers; no Homebrew or first-launch download required. Fixed upstream revisions, matching source archives and license notices ship together.
- macOS About/Finder version metadata now matches the application version.

- Compact system-themed Qt and GTK panels with aligned monitor rows and horizontal brightness presets.
- Bold tray brightness ring with confirmed values, per-screen selection, mixed-brightness and failure indicators.
- Tray-anchored Qt panel, dismiss-on-focus-loss behavior and keyboard dismissal; regular-window fallback without a tray host.
- GTK symbolic SVG icons with font outlines; deb now includes Cairo and the SVG loader.

## 1.1.0 — 2026-10-27 (Preview 1)

- Native Windows installer, macOS DMGs, gated GitHub prereleases and SHA-256 checksums.
- User-focused download pages and bilingual installation instructions.
- Shared Qt tray/panel frontend, retaining Ubuntu GTK compatibility.
- Windows DXVA2 DDC/CI and WMI adapters with scoped native handles and readback.
- macOS m1ddc, ddcctl and brightness adapters with helper discovery and device identity checks.
- Per-user Windows Run/macOS LaunchAgent startup and Qt single-instance IPC.
- Python packaging, PyInstaller builds, four-platform CI and a separate GTK job.
- English/Chinese documentation, contributor guidance and issue templates.
- Windows/macOS hardware remains experimental pending physical-device validation.

## 1.0.0 — 2026-10-23

- Ubuntu GTK/AppIndicator brightness panel, logind/ddcutil, presets and autostart.
- Simulated dual-monitor demo, unit/Xvfb tests and deb builder.
