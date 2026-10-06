"""The launcher for installed copies and the release archives the installers download."""
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import installed
import package_release


class InstalledTests(unittest.TestCase):
    def test_data_folder_and_node_come_first(self):
        install = Path('/install with spaces')
        node = install / 'runtime' / 'node'
        node = str(node if os.name == 'nt' else node / 'bin')
        environ = {'PATH': 'existing', 'ML_WORKSHOP_DATA_DIR': 'elsewhere'}
        installed.configure(environ, install)
        self.assertEqual(environ['ML_WORKSHOP_DATA_DIR'], str(install / 'data'))
        self.assertEqual(environ['PATH'], node + os.pathsep + 'existing')
        empty = {}
        installed.configure(empty, install)
        # A trailing separator would add the current folder to PATH.
        self.assertEqual(empty['PATH'], node)

    def test_start_errors_are_reported_and_stop_is_routed(self):
        with patch.object(installed, 'configure'), patch.object(installed, 'report') as report:
            with patch.object(installed.launch, 'main', side_effect=RuntimeError('Port 1 may be in use.')):
                self.assertEqual(installed.main([]), 1)
            report.assert_called_once_with('Port 1 may be in use.')
            with patch.object(installed.stop, 'main') as stop_main, patch.object(installed.launch, 'main') as launch_main:
                self.assertEqual(installed.main(['--stop']), 0)
            stop_main.assert_called_once_with()
            launch_main.assert_not_called()


class PackageReleaseTests(unittest.TestCase):
    def test_archives_hold_source_and_build_only(self):
        files = {
            'README.md': 'readme', 'install.sh': '#!/bin/sh\n', 'scripts/setup.py': '', 'docs/guide.md': 'public',
            '.gitignore': 'dist/\n__pycache__/\n', 'dist/index.html': '<!doctype html>',
            # Tracked or not, these must never reach a release.
            'docs/claude-notes.md': 'private', 'PLAN.md': 'private', 'data/workshop.sqlite3': 'progress',
            '.local/state': 'x', '.codex/environment.toml': 'x', 'scripts/__pycache__/setup.cpython-312.pyc': 'x',
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'checkout'
            for path, text in files.items():
                (root / path).parent.mkdir(parents=True, exist_ok=True)
                (root / path).write_text(text)
            (root / 'install.sh').chmod(0o755)
            git = ['git', '-c', 'user.name=Test', '-c', 'user.email=test@example.com', '-c', 'commit.gpgsign=false']
            subprocess.run(git + ['init', '-q'], cwd=root, check=True)
            subprocess.run(git + ['add', '--all'], cwd=root, check=True)
            subprocess.run(git + ['commit', '-q', '--no-verify', '-m', 'fixture'], cwd=root, check=True)
            (root / 'new.txt').write_text('untracked, not ignored')
            if os.name != 'nt':
                (root / 'node_modules').symlink_to(root / 'scripts')
            out = Path(directory) / 'release'
            tar_path, zip_path, sums_path = package_release.package(root, out)
            expected = {f'engineering-workshop/{path}' for path in
                        ['README.md', 'install.sh', 'scripts/setup.py', 'docs/guide.md', '.gitignore', 'dist/index.html', 'new.txt']}
            with tarfile.open(tar_path) as archive:
                self.assertEqual(set(archive.getnames()), expected)
                if os.name != 'nt':
                    self.assertEqual(archive.getmember('engineering-workshop/install.sh').mode, 0o755)
            with zipfile.ZipFile(zip_path) as archive:
                self.assertEqual(set(archive.namelist()), expected)
            sums = {line.split('  ')[1]: line.split('  ')[0] for line in sums_path.read_text().splitlines()}
            self.assertEqual(sums, {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in (tar_path, zip_path)})
            # The same checkout gives byte-identical archives.
            first = tar_path.read_bytes(), zip_path.read_bytes()
            package_release.package(root, out)
            self.assertEqual((tar_path.read_bytes(), zip_path.read_bytes()), first)

    def test_requires_a_built_interface(self):
        with tempfile.TemporaryDirectory() as directory, self.assertRaisesRegex(SystemExit, 'npm run build'):
            package_release.release_files(Path(directory))


if __name__ == '__main__':unittest.main()
