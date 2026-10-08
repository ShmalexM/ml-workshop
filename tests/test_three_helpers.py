"""Runs the browser-free checks for the hero game's three.js helpers with Node.js."""
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from runner import node_binary


def node_version(node):
    out = subprocess.run([node, '--version'], capture_output=True, text=True, check=True).stdout
    return tuple(int(part) for part in out.strip().lstrip('v').split('.')[:2])


class ThreeHelperTests(unittest.TestCase):
    def test_three_helpers(self):
        node = node_binary()
        if not node or not (ROOT / 'node_modules' / 'three').is_dir():
            self.skipTest('Needs Node.js and npm install.')
        # Node.js 22.6 and newer can load the TypeScript sources directly.
        if node_version(node) < (22, 6):
            self.skipTest('Needs Node.js 22.6 or newer.')
        result = subprocess.run([node, '--experimental-strip-types', '--no-warnings', 'tests/js/three_helpers.mjs'],
                                cwd=ROOT, capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertIn('three helpers ok', result.stdout)


if __name__ == '__main__':
    unittest.main()
