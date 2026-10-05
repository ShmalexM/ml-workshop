"""Setup selection and dependency skips without downloading packages."""
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
# Avoid an unrelated installed module named setup.
spec = importlib.util.spec_from_file_location('workshop_setup', ROOT / 'scripts/setup.py')
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)
from test_curriculum import missing_lesson_modules, require_lesson_modules


class SetupTests(unittest.TestCase):
    def test_lock_only_on_macos_arm64(self):
        for platform, machine, expected in [('darwin', 'arm64', 'requirements.lock'), ('darwin', 'x86_64', 'requirements.txt'), ('linux', 'aarch64', 'requirements.txt'), ('win32', 'AMD64', 'requirements.txt')]:
            with self.subTest(platform=platform, machine=machine), patch.object(sys, 'platform', platform), patch.object(setup.platform, 'machine', return_value=machine):
                self.assertEqual(setup.requirements_file().name, expected)
        self.assertEqual(setup.light_requirements(), ['pypdf>=6.19,<7'])

    def test_python_and_node_minimum_versions(self):
        with patch.object(sys, 'version_info', (3, 11)), self.assertRaisesRegex(RuntimeError, 'Python 3.12'):
            setup.check_prerequisites()
        for version, supported in [('v22.12.0', False), ('v22.13.0', True), ('v24.0.0', True), ('nonsense', False)]:
            with self.subTest(version=version), patch.object(setup.shutil, 'which', return_value='binary'), patch.object(setup.subprocess, 'check_output', return_value=version):
                if supported:self.assertEqual(setup.check_prerequisites(), 'binary')
                else:
                    with self.assertRaisesRegex(RuntimeError, 'Node.js 22.13'):setup.check_prerequisites()
        with patch.object(setup.shutil, 'which', return_value=None), self.assertRaisesRegex(RuntimeError, 'including npm'):
            setup.check_prerequisites()

    def test_uv_and_stdlib_install_build_and_no_launch(self):
        for uv in ('uv', None):
            with self.subTest(uv=uv), tempfile.TemporaryDirectory() as directory:
                python = Path(directory) / '.venv/bin/python'
                with patch.object(setup, 'venv_python', return_value=python), patch.object(setup, 'check_prerequisites', return_value='npm'), patch.object(setup.shutil, 'which', return_value=uv), patch.object(setup, 'run') as run:
                    setup.main(['--no-ml', '--no-launch'])
                commands = [call.args[0] for call in run.call_args_list]
                self.assertIn(['npm', 'ci'], commands)
                self.assertIn(['npm', 'run', 'build'], commands)
                self.assertFalse(any('launch.py' in str(arg) for command in commands for arg in command))
                if uv:
                    self.assertEqual(commands[0][:2], ['uv', 'venv'])
                    self.assertIn(['uv', 'pip', 'install', '--python', python, 'pypdf>=6.19,<7'], commands)
                else:
                    self.assertEqual(commands[0][:3], [sys.executable, '-m', 'venv'])
                    self.assertIn([python, '-m', 'ensurepip', '--upgrade'], commands)
                    self.assertIn([python, '-m', 'pip', 'install', 'pypdf>=6.19,<7'], commands)

    def test_full_install_launches_after_build(self):
        with patch.object(setup, 'check_prerequisites', return_value='npm'), patch.object(setup.shutil, 'which', return_value='uv'), patch.object(setup, 'run') as run:
            setup.main([])
        commands = [call.args[0] for call in run.call_args_list]
        self.assertIn(['uv', 'pip', 'install', '--python', setup.venv_python(), '-r', str(setup.requirements_file())], commands)
        self.assertEqual(commands[-2], ['npm', 'run', 'build'])
        self.assertEqual(commands[-1], [setup.venv_python(), ROOT / 'scripts/launch.py'])

    def test_missing_imports_skip_only_dependent_lessons(self):
        lesson = dict(id='fixture', starter='import torch', solution='from transformers import BertModel', example={'code': 'print(1)'})
        with patch.object(importlib.util, 'find_spec', side_effect=lambda name: None if name == 'torch' else object()):
            self.assertEqual(missing_lesson_modules(lesson), ['torch'])
            with patch.dict(os.environ, {'ML_WORKSHOP_REQUIRE_ML': '0'}), self.assertRaises(unittest.SkipTest):
                require_lesson_modules(self, lesson)
            with patch.dict(os.environ, {'ML_WORKSHOP_REQUIRE_ML': '1'}), self.assertRaises(AssertionError):
                require_lesson_modules(self, lesson)
        self.assertEqual(missing_lesson_modules({**lesson, 'language': 'javascript'}), [])


if __name__ == '__main__':unittest.main()
