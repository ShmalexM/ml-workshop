"""Update controls use fixed release sources, stable runtime workers and preserved data."""
from contextlib import ExitStack
from datetime import datetime, timedelta, timezone
import io
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock, patch
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'backend'))
import app_update
import update_worker
from server_fixture import server_token


class UpdateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='ml-update-test-')
        self.addCleanup(self.tmp.cleanup)
        self.install = Path(self.tmp.name).resolve() / 'installed with spaces'
        self.root = self.install / 'app'
        self.data = self.install / 'data'
        (self.root / 'scripts').mkdir(parents=True)
        self.data.mkdir()
        (self.install / '.engineering-workshop').write_text('fixture')
        shutil.copyfile(ROOT / 'scripts/update_worker.py', self.root / 'scripts/update_worker.py')
        for suffix in ('sh', 'ps1'):
            (self.root / ('install.' + suffix)).write_text('fixture installer')
        self.updater = app_update.Updater(self.root, self.data, '1.2.0')

    def release(self, tag='v1.3.0', **extra):
        body = dict(tag_name=tag, draft=False, prerelease=False, **extra)
        return io.BytesIO(json.dumps(body).encode())

    def selected(self):
        update_worker.write_status(self.data, latestVersion='1.3.0', status='idle')

    def test_default_source_and_custom_installation_guidance_is_truthful(self):
        initial = self.updater.status()
        self.assertTrue(initial['installed'])
        self.assertTrue(initial['supported'])
        self.assertEqual(initial['currentVersion'], '1.2.0')
        self.assertIsNone(initial['latestVersion'])
        source = app_update.Updater(ROOT, self.data, '1.2.0')
        self.assertFalse(source.status()['supported'])
        self.assertIn('source checkout', source.status()['message'])
        other = self.install / 'custom-data'
        other.mkdir()
        self.assertFalse(app_update.Updater(self.root, other, '1.2.0').supported())
        self.updater.base_python = self.root / 'python'
        self.updater.base_python.touch()
        self.assertFalse(self.updater.supported())

    def test_check_uses_only_fixed_metadata_source_and_numeric_versions(self):
        with patch.object(app_update.urllib.request, 'urlopen', return_value=self.release()) as request:
            status = self.updater.check({})
        self.assertEqual(request.call_args.args[0].full_url, app_update.LATEST_API)
        self.assertEqual(request.call_args.kwargs['timeout'], 10)
        self.assertEqual(status['latestVersion'], '1.3.0')
        self.assertTrue(status['updateAvailable'])
        self.assertEqual(status['releaseUrl'], 'https://github.com/ShmalexM/ml-workshop/releases/tag/v1.3.0')
        self.assertIsNotNone(status['checkedAt'])
        self.assertTrue(app_update.newer('1.10.0', '1.9.0'))
        self.assertFalse(app_update.newer('1.2.0', '1.3.0'))

    def test_offline_invalid_or_prerelease_metadata_is_a_retryable_error(self):
        for response in (OSError('offline'), self.release('v1.3.0-beta.1'), self.release('../malicious'),
                         self.release('v1.3.0', url='https://attacker.example/'), io.BytesIO(b'[' * 2000)):
            with self.subTest(response=type(response).__name__):
                arbitrary_url = isinstance(response, io.BytesIO) and b'attacker' in response.getvalue()
                if isinstance(response, BaseException):
                    context = patch.object(app_update.urllib.request, 'urlopen', side_effect=response)
                else:
                    context = patch.object(app_update.urllib.request, 'urlopen', return_value=response)
                with context:
                    status = self.updater.check({})
                # Arbitrary metadata URLs are ignored; a valid stable tag alone remains usable.
                if arbitrary_url:
                    self.assertEqual(status['status'], 'idle')
                    self.assertNotIn('attacker', status['releaseUrl'])
                else:
                    self.assertEqual(status['status'], 'error')
                    self.assertIn('try again', status['error'])

    def test_actions_reject_any_client_paths_urls_or_nonempty_values(self):
        for body in (None, [], True, {'url': 'https://attacker.example'}, {'archive': '/tmp/app'}, {'force': True}):
            for method in (lambda value: self.updater.check(value), lambda value: self.updater.apply(value, 7318, Mock())):
                with self.subTest(body=body), self.assertRaises(ValueError):
                    method(body)

    def test_apply_copies_worker_outside_app_and_bootstraps_with_stable_runtime(self):
        self.selected()
        backup = Mock()
        with patch.object(app_update.subprocess, 'run', return_value=types.SimpleNamespace(returncode=0, stdout='12345\n')) as start:
            result = self.updater.apply({}, 7386, backup)
        backup.assert_called_once_with()
        command = start.call_args.args[0]
        self.assertEqual(command[0], str(self.updater.base_python))
        self.assertFalse(Path(command[0]).is_relative_to(self.root))
        self.assertEqual(command[1], str(self.data / 'update-work/update_worker.py'))
        self.assertIn('--bootstrap', command)
        self.assertEqual(command[command.index('--port') + 1], '7386')
        self.assertEqual(command[command.index('--target') + 1], '1.3.0')
        self.assertEqual((self.data / 'update-work/update_worker.py').read_bytes(), (ROOT / 'scripts/update_worker.py').read_bytes())
        self.assertEqual(result['status'], 'updating')
        self.assertEqual(start.call_args.kwargs['env']['EW_RELEASE_TAG'], 'v1.3.0')

    def test_duplicate_apply_and_busy_check_never_launch_another_worker(self):
        self.selected()
        update_worker.write_status(self.data, status='updating', pid=os.getpid(), startedAt=update_worker.timestamp())
        with patch.object(app_update.subprocess, 'run') as start:
            for action in (lambda: self.updater.apply({}, 7318, Mock()), lambda: self.updater.check({})):
                with self.assertRaises(app_update.UpdateConflict):
                    action()
        start.assert_not_called()

    def test_failed_bootstrap_is_reported_without_touching_app_or_data(self):
        self.selected()
        (self.data / 'book-sentinel').write_text('keep book')
        with patch.object(app_update.subprocess, 'run', side_effect=OSError('cannot spawn')):
            result = self.updater.apply({}, 7318, Mock())
        self.assertEqual(result['status'], 'error')
        self.assertIn('could not start', result['error'])
        self.assertTrue(result['updateAvailable'])
        self.assertEqual((self.data / 'book-sentinel').read_text(), 'keep book')
        self.assertTrue((self.root / 'install.sh').is_file())

    def test_interrupted_check_and_dead_worker_recover_to_retryable_status(self):
        old = (datetime.now(timezone.utc) - timedelta(minutes=2)).isoformat()
        for status in ('checking', 'updating', 'restarting'):
            with self.subTest(status=status):
                update_worker.write_status(self.data, status=status, pid=99999999, startedAt=old)
                self.assertEqual(self.updater.status()['status'], 'error')
        update_worker.write_status(self.data, status='updating', pid=None, startedAt=update_worker.timestamp())
        self.assertTrue(self.updater.busy())

    def test_environment_drops_credentials_archive_override_and_keeps_fixed_parameters(self):
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'secret', 'EW_ARCHIVE': '/untrusted', 'PYTHONPATH': '/untrusted',
                                     'EW_KEEP_OLD': '0', 'PROCESSOR_ARCHITECTURE': 'x86', 'PROCESSOR_ARCHITEW6432': 'AMD64'}):
            env = update_worker.installer_environment(self.install, self.data, 7386, '1.3.0', True)
        for name in ('OPENAI_API_KEY', 'EW_ARCHIVE', 'PYTHONPATH'):
            self.assertNotIn(name, env)
        self.assertEqual(env['EW_KEEP_OLD'], '1')
        self.assertEqual(env['EW_NO_LAUNCH'], '1')
        self.assertEqual(env['EW_NO_SHORTCUTS'], '1')
        self.assertEqual(env['ML_WORKSHOP_DATA_DIR'], str(self.data))
        self.assertEqual(env['ML_WORKSHOP_PORT'], '7386')
        self.assertEqual(env['EW_REQUIRE_ML'], '0')
        # Windows PowerShell 5.1 uses these when RuntimeInformation is unavailable.
        self.assertEqual(env['PROCESSOR_ARCHITECTURE'], 'x86')
        self.assertEqual(env['PROCESSOR_ARCHITEW6432'], 'AMD64')
        self.assertEqual(update_worker.installer_environment(self.install, self.data, 7386, '1.3.0', False)['EW_REQUIRE_ML'], '1')

    def test_commands_are_argument_lists_on_windows_and_posix(self):
        file = Path('/installation with spaces/update.ps1')
        windows = update_worker.installer_command(file, 'win32')
        self.assertEqual(windows, ['powershell.exe', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-File', str(file)])
        self.assertEqual(update_worker.installer_command(file, 'darwin'), ['/bin/sh', str(file)])

    def test_bootstrap_passes_its_pid_and_worker_waits_before_continuing(self):
        args = ['--install', str(self.install), '--data', str(self.data), '--port', '7386', '--target', '1.3.0', '--previous', '1.2.0']
        with patch.object(update_worker.subprocess, 'Popen', return_value=types.SimpleNamespace(pid=1234)) as spawn, patch('builtins.print'):
            update_worker.bootstrap(args)
        command = spawn.call_args.args[0]
        self.assertEqual(command[-2:], ['--bootstrap-pid', str(os.getpid())])
        if os.name != 'nt':
            with patch.object(update_worker.os, 'kill', side_effect=[None, ProcessLookupError]), patch.object(update_worker.time, 'sleep') as sleep:
                update_worker.wait_bootstrap_exit(1234)
            sleep.assert_called_once_with(.1)

    def test_worker_shared_installer_lock_prevents_manual_update_races_and_rollback(self):
        with update_worker.install_lock(self.install):
            with patch.object(update_worker, 'perform_update') as update:
                update_worker.run_update(self.install, self.data, 7386, '1.3.0', '1.2.0', True)
                update.assert_not_called()
            self.assertEqual(update_worker.read_status(self.data)['status'], 'error')
            self.assertIn('Another installer', update_worker.read_status(self.data)['error'])
        self.assertFalse((self.install / '.install-lock').exists())

    def test_worker_success_checks_health_before_removing_old_app(self):
        old = self.install / '.app-old'
        old.mkdir()
        (old / 'previous').write_text('old')
        (self.data / 'book-sentinel').write_text('keep book')
        with patch.object(update_worker, 'run_installer', return_value=0), patch.object(update_worker, 'restart') as restart, \
                patch.object(update_worker, 'wait_healthy', return_value=True) as health:
            update_worker.run_update(self.install, self.data, 7386, '1.3.0', '1.2.0', True)
        restart.assert_called_once()
        health.assert_called_once_with(7386, self.data, '1.3.0')
        self.assertEqual(update_worker.read_status(self.data)['status'], 'updated')
        self.assertFalse(old.exists())
        self.assertEqual((self.data / 'book-sentinel').read_text(), 'keep book')
        self.assertFalse((self.install / '.install-lock').exists())

    def test_install_or_health_failure_restores_previous_version_under_lock(self):
        for install_error in (False, True):
            with self.subTest(install_error=install_error):
                with patch.object(update_worker, 'run_installer', return_value=1 if install_error else 0), \
                        patch.object(update_worker, 'restart'), patch.object(update_worker, 'wait_healthy', return_value=False), \
                        patch.object(update_worker, 'rollback', return_value=True) as rollback:
                    update_worker.run_update(self.install, self.data, 7386, '1.3.0', '1.2.0', True)
                self.assertEqual(rollback.call_args.args[:4], (self.install, self.data, 7386, '1.2.0'))
                self.assertEqual(update_worker.read_status(self.data)['status'], 'error')
                self.assertIn('previous version is running', update_worker.read_status(self.data)['error'])

    def test_rollback_moves_only_application_and_restarts_previous_with_same_data_port(self):
        old = self.install / '.app-old'
        old.mkdir()
        (old / 'previous').write_text('old')
        (self.data / 'profile-sentinel').write_text('keep profile')
        env = update_worker.installer_environment(self.install, self.data, 7386, '1.3.0', True)
        with patch.object(update_worker.subprocess, 'run', return_value=types.SimpleNamespace(returncode=0)), \
                patch.object(update_worker, 'restart') as restart, patch.object(update_worker, 'wait_healthy', return_value=True):
            self.assertTrue(update_worker.rollback(self.install, self.data, 7386, '1.2.0', env))
        self.assertEqual((self.root / 'previous').read_text(), 'old')
        self.assertEqual((self.data / 'profile-sentinel').read_text(), 'keep profile')
        self.assertEqual(restart.call_args.args, (self.install, env))

    def test_failed_stage_rename_restores_old_app_without_trying_missing_new_python(self):
        old = self.install / '.app-old'
        self.root.rename(old)
        (old / 'previous').write_text('old')
        env = update_worker.installer_environment(self.install, self.data, 7386, '1.3.0', True)
        with patch.object(update_worker.subprocess, 'run') as stop, patch.object(update_worker, 'restart'), \
                patch.object(update_worker, 'wait_healthy', return_value=True):
            self.assertTrue(update_worker.rollback(self.install, self.data, 7386, '1.2.0', env))
        stop.assert_not_called()
        self.assertEqual((self.root / 'previous').read_text(), 'old')


class UpdateApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix='ml-update-api-')
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            cls.port = sock.getsockname()[1]
        cls.url = f'http://127.0.0.1:{cls.port}'
        cls.proc = subprocess.Popen([sys.executable, str(ROOT / 'backend/server.py'), '--port', str(cls.port)],
                                    env={**os.environ, 'ML_WORKSHOP_DATA_DIR': cls.tmp.name},
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        cls.token = server_token(cls.url, cls.tmp.name, cls.proc)

    @classmethod
    def tearDownClass(cls):
        cls.proc.terminate(); cls.proc.wait(timeout=10); cls.tmp.cleanup()

    def request(self, path, body=None, token=None):
        data = json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request(self.url + path, data=data,
                                         headers={'Content-Type': 'application/json', 'X-Workshop-Token': token if token is not None else self.token})
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)

    def test_status_and_actions_are_authenticated_and_source_apply_is_disabled(self):
        self.assertFalse(self.request('/api/update')['supported'])
        for path, body in (('/api/update', None), ('/api/update/check', {}), ('/api/update/apply', {})):
            with self.subTest(path=path), self.assertRaises(urllib.error.HTTPError) as error:
                self.request(path, body, token='wrong')
            self.assertEqual(error.exception.code, 403)
        with self.assertRaises(urllib.error.HTTPError) as error:
            self.request('/api/update/apply', {})
        self.assertEqual(error.exception.code, 409)

    def test_unknown_update_action_parameters_are_rejected_before_any_network_or_install(self):
        for path in ('/api/update/check', '/api/update/apply'):
            with self.subTest(path=path), self.assertRaises(urllib.error.HTTPError) as error:
                self.request(path, {'url': 'https://attacker.example/'})
            self.assertEqual(error.exception.code, 400)

    def test_active_update_blocks_new_exercises_and_assistant_but_keeps_drafts(self):
        update_worker.write_status(self.tmp.name, status='updating', startedAt=update_worker.timestamp(), pid=os.getpid())
        try:
            for path, body in (('/api/run', dict(lessonId='python-1', code='print(1)', mode='run')),
                               ('/api/example', dict(lessonId='python-1')), ('/api/assistant/chat', {})):
                with self.subTest(path=path), self.assertRaises(urllib.error.HTTPError) as error:
                    self.request(path, body)
                self.assertEqual(error.exception.code, 409)
            self.assertTrue(self.request('/api/draft', dict(lessonId='python-1', code='print(2)', notes='keep', updatedAt=100))['applied'])
            self.assertEqual(self.request('/api/state')['notes']['python-1'], 'keep')
        finally:
            update_worker.write_status(self.tmp.name, status='idle')


if __name__ == '__main__':
    unittest.main()
