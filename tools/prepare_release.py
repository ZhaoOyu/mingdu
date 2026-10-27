#!/usr/bin/env python3
"""Reject incomplete/ambiguous artifacts and assemble the public release assets."""
import argparse
import hashlib
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from brightness import __version__


def prepare(source, destination, tag):
    if not tag.startswith(f'v{__version__}-preview.') or not tag.rsplit('.', 1)[-1].isdigit():
        raise ValueError(f'Expected v{__version__}-preview.<number>, got {tag!r}')
    names = [f'mingdu_{__version__}_all.deb',
             f'mingdu-{__version__}-linux-x86_64.tar.gz',
             f'mingdu-{__version__}-windows-x86_64-setup.exe',
             f'mingdu-{__version__}-windows-x86_64.zip',
             f'mingdu-{__version__}-macos-arm64.dmg',
             f'mingdu-{__version__}-macos-x86_64.dmg']
    selected = []
    for name in names:
        matches = list(source.rglob(name))
        if len(matches) != 1 or matches[0].stat().st_size == 0:
            raise ValueError(f'Expected exactly one nonempty artifact: {name}')
        selected.append(matches[0])
    destination.mkdir(parents=True, exist_ok=False)
    for path in selected:
        shutil.copy2(path, destination / path.name)
    shutil.copy2(ROOT / 'docs/INSTALL.md', destination / 'INSTALL.md')
    checksums = []
    for path in sorted(destination.iterdir()):
        hasher = hashlib.sha256()
        with path.open('rb') as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                hasher.update(chunk)
        digest = hasher.hexdigest()
        checksums.append(f'{digest}  {path.name}\n')
    (destination / 'SHA256SUMS.txt').write_text(''.join(checksums), encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('source', type=Path)
    parser.add_argument('destination', type=Path)
    parser.add_argument('tag')
    args = parser.parse_args()
    prepare(args.source, args.destination, args.tag)
