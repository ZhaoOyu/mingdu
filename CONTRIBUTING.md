# Contributing to Mingdu

Issues and pull requests are welcome in English or Chinese.

## Development

Use Python 3.10 or newer in a virtual environment:

```sh
python -m pip install -e ".[qt,build]" ruff
python -m brightness --demo --ui qt
python -m unittest discover -s tests -v
python tests/qt_smoke.py
python -m ruff check .
```

`--demo` never communicates with physical displays. Unit tests inject hardware adapters; CI must not write to physical displays. Tests of real equipment should record OS, architecture, display model, connection path, helper version and whether readback agrees with the monitor's OSD. Redact serial numbers and personal device identifiers before posting diagnostics.

## Design

- `backends.py`: common display model and Linux driver.
- `platforms/`: lazy-selected Windows and macOS drivers.
- `worker.py`: one serial hardware worker; coalesce pending slider requests per device.
- `macos_app.py`: native AppKit popover, SF Symbols and system controls; default on macOS.
- `native_controller.py`: main-thread state and queued hardware results for AppKit.
- `native_instance.py`: macOS process lock and activation notifications.
- `qt_app.py`: Windows/Linux panel, tray and controller (optional source frontend on macOS). GUI state is updated on the main thread.
- `app.py`: maintained GTK compatibility frontend for the small Ubuntu deb package.
- `tools/build_macos_helpers.py`: pinned upstream helper builds, source archives and notices for macOS bundles.
- `startup.py`: per-user startup registration; do not request admin privileges.

Prefer small changes and tests for observable behavior. Preserve read-only startup: discovering a display must never change its brightness. Never invent a successful hardware result when reads fail. Keep optional controls capability-driven and isolate a faulty monitor from the rest.

## Packaging

macOS builds require Git and Xcode command-line tools. The build fetches fixed upstream helper commits, builds the matching architecture, and includes executable helpers plus their licenses and exact source archives; no Homebrew is needed at runtime.

Run `python tools/build_desktop.py` on the OS/architecture being packaged. macOS Intel and Apple Silicon archives are separate. CI archives are unsigned development builds; release signing and notarization require maintainer credentials. Do not commit credentials or helper binaries.

After building the bundle, `python tools/build_installers.py` creates and validates native installers (Windows needs Inno Setup 6; macOS uses hdiutil). Ubuntu deb uses `python tools/build_deb.py`. See [release workflow](docs/RELEASING.md) for preview publication.

The project code is MIT-licensed. Third-party components keep their own licenses; see `THIRD_PARTY_NOTICES.md`. Contributions are provided under the project license.
