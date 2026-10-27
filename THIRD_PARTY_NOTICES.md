# Third-party components

Mingdu's own Python code is licensed under MIT (see `LICENSE`). This does not replace the licenses of its dependencies.

## Qt frontend and frozen desktop builds

- [PySide6 / Qt for Python](https://doc.qt.io/qtforpython-6/licenses.html), including Shiboken: available under LGPLv3/GPLv3 or commercial terms. This project uses the open-source packages. Qt libraries have their respective upstream licenses.
- Frozen distributions keep Qt/PySide shared libraries in a replaceable directory/framework layout. Installed PySide6-Essentials and Shiboken distribution metadata is copied into the bundle; LGPLv3/GPLv3 texts are included under `docs/licenses`. Upstream sources and license texts: [Qt source repositories](https://code.qt.io/), [PySide setup](https://code.qt.io/pyside/pyside-setup.git/), [LGPLv3](https://www.gnu.org/licenses/lgpl-3.0.html). Use the version recorded in bundled package metadata to locate corresponding upstream sources. You may modify/replace these LGPL libraries and reverse-engineer the application for debugging such modifications under the LGPL's terms.
- [Python](https://www.python.org/psf/license/) is distributed under the Python Software Foundation license and included third-party notices.
- [PyInstaller](https://pyinstaller.org/en/stable/license.html) uses GPLv2 with an exception permitting applications built with it to retain their own licenses. Build tooling is not an additional restriction on Mingdu's MIT source.

## GTK frontend

PyGObject, GTK and Ayatana AppIndicator are separately installed distribution packages with their own licenses. The Ubuntu source-based deb does not bundle these libraries.

## Hardware helpers

The following tools are invoked as independent, user-installed executables. Their code or binaries are not copied into this repository or desktop bundles:

- [ddcutil](https://github.com/rockowitz/ddcutil) — Linux DDC/CI.
- [m1ddc](https://github.com/waydabber/m1ddc) — Apple Silicon DDC/CI, MIT.
- [ddcctl](https://github.com/kfix/ddcctl) — Intel Mac DDC/CI, GPLv3.
- [brightness](https://github.com/nriley/brightness) — Apple/native macOS backlight controls, MIT.

Windows User32, DXVA2, PowerShell and WMI are operating-system components and are not redistributed by Mingdu.
