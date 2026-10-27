# Mingdu · 明度

**Comfortable brightness for every screen, right from your tray.**

Mingdu is a free, open-source brightness controller for Ubuntu, macOS and Windows. Adjust your laptop screen and external monitors without reaching for their physical buttons.

[Download preview](https://github.com/ZhaoOyu/mingdu/releases/tag/v1.1.0-preview.1) · [Installation guide](docs/INSTALL.md#english-quick-start) · [Report an issue](https://github.com/ZhaoOyu/mingdu/issues) · [简体中文](README.md)

<p align="center"><img src="docs/preview.png" width="420" alt="Mingdu panel with independent monitor sliders, brightness presets and login startup" /></p>
<p align="center"><sub>Qt interface with simulated monitors. The Ubuntu deb uses a native GTK interface. The current application UI is Chinese.</sub></p>

## Your screens, within reach

- **Independent controls** for each display, plus adjustments for all screens together.
- **Tray access** and a slider panel that stays available in the background.
- **One-click presets** for evening, everyday use and brighter environments.
- **Real hardware brightness** through system backlight interfaces or DDC/CI, without dark overlays.
- **Optional login startup** that reads your current brightness without changing it.
- **Local and private** — no account, telemetry or display information uploads. MIT licensed.

## Download

**1.1.0 Preview 1** is available for early adopters. Automated builds and simulated-device tests pass across platforms; physical monitor compatibility is still being collected. This is not a stable release.

| Platform | Download | Installation |
|---|---|---|
| Ubuntu 22.04 / 24.04 / 26.04 | [.deb](https://github.com/ZhaoOyu/mingdu/releases/download/v1.1.0-preview.1/mingdu_1.1.0_all.deb) | Install using apt |
| macOS 15+ · Apple Silicon | [arm64 .dmg](https://github.com/ZhaoOyu/mingdu/releases/download/v1.1.0-preview.1/mingdu-1.1.0-macos-arm64.dmg) | Drag to Applications; install hardware helpers as needed |
| macOS 15+ · Intel | [x86_64 .dmg](https://github.com/ZhaoOyu/mingdu/releases/download/v1.1.0-preview.1/mingdu-1.1.0-macos-x86_64.dmg) | Drag to Applications; install hardware helpers as needed |
| Windows 10 / 11 · x64 | [Installer](https://github.com/ZhaoOyu/mingdu/releases/download/v1.1.0-preview.1/mingdu-1.1.0-windows-x86_64-setup.exe) | Install for your user; no separate Python installation |

The [release page](https://github.com/ZhaoOyu/mingdu/releases/tag/v1.1.0-preview.1) also includes a Windows portable ZIP, Linux Qt archive and SHA-256 checksums. Windows and macOS previews do not yet have trusted code signing or Apple notarization and may be blocked on first launch. See the [installation guide](docs/INSTALL.md#english-quick-start).

## Get started

Launch Mingdu, open its tray panel, then move a display slider or select a preset. Refresh after connecting a monitor, waking your computer or changing brightness elsewhere. Enable login startup from the application if desired.

On Ubuntu, run these commands from your download directory:

```sh
sudo apt install ./mingdu_1.1.0_all.deb
mingdu
```

Enable **DDC/CI** in your external monitor's own menu first. Built-in screens need a supported system backlight interface. HDR modes, docks, KVMs, adapters and DisplayLink connections can affect compatibility. macOS requires external helper tools; see the installation guide.

This release controls brightness only. Contrast, volume and input switching are not included. Tray scrolling depends on the desktop environment; the slider panel works across platforms.

## Help more monitors work

Share your OS, monitor model and connection details in a [compatibility report](https://github.com/ZhaoOyu/mingdu/issues/new/choose), or contribute code, documentation and translations.

[Contributing](CONTRIBUTING.md) · [Changelog](CHANGELOG.md) · [Test coverage](TESTING.md) · [Security](SECURITY.md)

Mingdu is [MIT licensed](LICENSE). Dependencies retain their own licenses; see [third-party notices](THIRD_PARTY_NOTICES.md).
