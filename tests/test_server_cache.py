"""Package versions are read once and again only after a package folder changes. The slow first answers are prepared at start."""
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
import server


class PackageVersionTests(unittest.TestCase):
    def setUp(self):
        server.runtime_cache = None
        self.addCleanup(setattr, server, 'runtime_cache', None)

    def test_versions_are_read_again_only_after_a_package_folder_changes(self):
        installed, calls = {'torch': '2.0.0', 'numba': '0.60.0'}, []
        def version(name):
            calls.append(name)
            if name not in installed:raise server.PackageNotFoundError(name)
            return installed[name]
        reads = len(server.RUNTIME_PACKAGES)
        with tempfile.TemporaryDirectory() as folder, patch.object(server, 'version', version), patch.object(sys, 'path', [folder, *sys.path]):
            first = server.runtime()
            self.assertEqual(first['packages'], {name: installed.get(name) for name in server.RUNTIME_PACKAGES})
            self.assertEqual(server.runtime(), first)
            self.assertEqual(len(calls), reads)
            # A caller that changes its answer does not change the next one.
            first['packages']['torch'] = 'changed'
            self.assertEqual(server.runtime()['packages']['torch'], '2.0.0')
            self.assertEqual(len(calls), reads)
            # Installing, upgrading or removing a package changes the time of the folder that holds it.
            installed['tensorflow'] = '2.16.0';del installed['numba']
            changed = os.stat(folder).st_mtime_ns + 10**9
            os.utime(folder, ns=(changed, changed))
            packages = server.runtime()['packages']
            self.assertEqual((packages['tensorflow'], packages['numba']), ('2.16.0', None))
            self.assertEqual(len(calls), 2 * reads)
            self.assertEqual(server.runtime()['packages'], packages)
            self.assertEqual(len(calls), 2 * reads)

    def test_a_missing_folder_on_the_path_is_not_an_error(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(sys, 'path', [str(Path(folder) / 'missing'), *sys.path]):
            self.assertEqual(set(server.runtime()['packages']), set(server.RUNTIME_PACKAGES))

    def test_warm_prepares_the_curriculum_and_the_versions(self):
        server.warm()
        self.assertIsNotNone(server.runtime_cache)
        self.assertEqual(server.public_curriculum.cache_info().currsize, 1)
        self.assertIs(server.curriculum(), server.public_curriculum())


if __name__ == '__main__':
    unittest.main()
