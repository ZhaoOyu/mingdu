import hashlib
from pathlib import Path
import tempfile
import unittest

from tools.prepare_release import prepare


class ReleaseTests(unittest.TestCase):
    def make_artifacts(self, root):
        names = ['mingdu_1.1.0_all.deb', 'mingdu-1.1.0-linux-x86_64.tar.gz',
                 'mingdu-1.1.0-windows-x86_64-setup.exe', 'mingdu-1.1.0-windows-x86_64.zip',
                 'mingdu-1.1.0-macos-arm64.dmg', 'mingdu-1.1.0-macos-x86_64.dmg']
        for index, name in enumerate(names):
            directory = root / str(index)
            directory.mkdir(parents=True)
            (directory / name).write_bytes(b'package payload')
        return names

    def test_complete_release_and_hashes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            names = self.make_artifacts(root / 'input')
            output = root / 'output'
            prepare(root / 'input', output, 'v1.1.0-preview.1')
            self.assertEqual({p.name for p in output.iterdir()}, set(names + ['INSTALL.md', 'SHA256SUMS.txt']))
            for line in (output / 'SHA256SUMS.txt').read_text().splitlines():
                digest, name = line.split('  ')
                self.assertEqual(digest, hashlib.sha256((output / name).read_bytes()).hexdigest())

    def test_reject_missing_duplicate_empty_or_wrong_tag_before_output(self):
        for failure in ('missing', 'duplicate', 'empty', 'tag'):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                names = self.make_artifacts(root / 'input')
                first = root / 'input/0' / names[0]
                tag = 'v1.1.0-preview.1'
                if failure == 'missing':
                    first.unlink()
                elif failure == 'duplicate':
                    (root / 'input' / names[0]).write_bytes(b'duplicate')
                elif failure == 'empty':
                    first.write_bytes(b'')
                else:
                    tag = 'v9.0.0-preview.1'
                with self.assertRaises(ValueError):
                    prepare(root / 'input', root / 'output', tag)
                self.assertFalse((root / 'output').exists())
