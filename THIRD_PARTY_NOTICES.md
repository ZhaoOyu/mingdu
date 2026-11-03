# Third-party components

Mingdu's own Python code is licensed under MIT (see `LICENSE`). This does not replace the licenses of its dependencies.

## macOS AppKit frontend

The native macOS application uses system AppKit/Foundation through PyObjC (MIT). PyObjC distribution metadata and `licenses/PyObjC-LICENSE.txt` are included in the bundle. The native Mac bundle does not include Qt.

## Qt frontend and Windows/Linux frozen desktop builds

- [PySide6 / Qt for Python](https://doc.qt.io/qtforpython-6/licenses.html), including Shiboken: available under LGPLv3/GPLv3 or commercial terms. This project uses the open-source packages. Qt libraries have their respective upstream licenses.
- Frozen distributions keep Qt/PySide shared libraries in a replaceable directory/framework layout. Installed PySide6-Essentials and Shiboken distribution metadata is copied into the bundle; LGPLv3/GPLv3 texts are included under `docs/licenses`. Upstream sources and license texts: [Qt source repositories](https://code.qt.io/), [PySide setup](https://code.qt.io/pyside/pyside-setup.git/), [LGPLv3](https://www.gnu.org/licenses/lgpl-3.0.html). Use the version recorded in bundled package metadata to locate corresponding upstream sources. You may modify/replace these LGPL libraries and reverse-engineer the application for debugging such modifications under the LGPL's terms.
- [Python](https://www.python.org/psf/license/) is distributed under the Python Software Foundation license and included third-party notices.
- [PyInstaller](https://pyinstaller.org/en/stable/license.html) uses GPLv2 with an exception permitting applications built with it to retain their own licenses. Build tooling is not an additional restriction on Mingdu's MIT source.

## GTK frontend

PyGObject, Pycairo/Cairo, librsvg, GTK and Ayatana AppIndicator are separately installed distribution packages with their own licenses. The Ubuntu source-based deb does not bundle these libraries.

## Hardware helpers

macOS builds compile pinned upstream revisions and include the tools as separate executables. They are invoked as subprocesses rather than linked into Mingdu. Each tool retains its own license:

- [brightness](https://github.com/nriley/brightness) — Apple backlight, BSD-2-Clause.
- [m1ddc](https://github.com/waydabber/m1ddc) — Apple Silicon DDC/CI, MIT.
- [ddcctl](https://github.com/kfix/ddcctl) — Intel Mac DDC/CI, GPLv3.

The app includes exact corresponding source archives (including Makefiles), license notices, source revisions, source checksums and rebuild instructions under `Contents/Resources/docs/helpers`. Only the helpers appropriate for the package's architecture are included. Pinned revisions are maintained in `tools/build_macos_helpers.py`; generated binaries are not committed to this repository.

[ddcutil](https://github.com/rockowitz/ddcutil) remains a separately installed Linux package and is not bundled.

Windows User32, DXVA2, PowerShell and WMI are operating-system components and are not redistributed by Mingdu.
