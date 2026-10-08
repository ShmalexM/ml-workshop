"""Platform branches plus a real launcher lifecycle on an unused loopback port."""
from contextlib import ExitStack
import json
import os
from pathlib import Path
import signal
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
import launch
import platform_paths as paths
import stop


class PlatformPathsTests(unittest.TestCase):
    def test_venv_paths(self):
        root = Path('/checkout with spaces')
        for platform, suffix in [('darwin', 'bin/python'), ('linux', 'bin/python'), ('win32', 'Scripts/python.exe')]:
            with self.subTest(platform=platform), patch.object(sys, 'platform', platform):
                self.assertEqual(paths.venv_python(root), root / '.venv' / suffix)

    def test_data_and_port_defaults_and_overrides(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.dict(os.environ, {}, clear=True):
                self.assertEqual(paths.data_dir(root), (root / 'data').resolve())
                self.assertEqual(paths.port(), 7318)  # No connection to this port.
            with patch.dict(os.environ, {'ML_WORKSHOP_DATA_DIR': 'relative data', 'ML_WORKSHOP_PORT': '17319'}):
                self.assertEqual(paths.data_dir(root), (root / 'relative data').resolve())
                self.assertEqual(paths.port(), 17319)
            with patch.dict(os.environ, {'ML_WORKSHOP_DATA_DIR': directory}):
                self.assertEqual(paths.data_dir(root), root.resolve())
            for value in ('0', '-1', '65536', 'bad'):
                with patch.dict(os.environ, {'ML_WORKSHOP_PORT': value}), self.assertRaises(ValueError):
                    paths.port()

    def test_installed_copy_keeps_data_next_to_the_app(self):
        # Updates replace app/, so tools must not default to app/data in an installed copy.
        with tempfile.TemporaryDirectory() as directory:
            install = Path(directory) / 'install folder'
            app = install / 'app'
            app.mkdir(parents=True)
            with patch.dict(os.environ, {}, clear=True):
                self.assertFalse(paths.installed(app))
                self.assertEqual(paths.data_dir(app), (app / 'data').resolve())
                (install / paths.INSTALL_MARKER).write_text('Created by the Engineering Workshop installer.')
                self.assertTrue(paths.installed(app))
                self.assertEqual(paths.data_dir(app), (install / 'data').resolve())
                # A clone that is not named app/ is never treated as installed.
                clone = install / 'ml-workshop'
                clone.mkdir()
                self.assertFalse(paths.installed(clone))
                self.assertEqual(paths.data_dir(clone), (clone / 'data').resolve())
            with patch.dict(os.environ, {'ML_WORKSHOP_DATA_DIR': str(install / 'elsewhere')}):
                self.assertEqual(paths.data_dir(app), (install / 'elsewhere').resolve())

    def test_session_token_is_private_and_kept(self):
        with tempfile.TemporaryDirectory() as directory:
            data = Path(directory)
            self.assertIsNone(paths.read_session_token(data))
            token = paths.session_token(data)
            self.assertRegex(token, r'^[A-Za-z0-9_-]{43}$')
            # A restart reads the same token, so open pages keep working.
            self.assertEqual(paths.session_token(data), token)
            self.assertEqual(paths.read_session_token(data), token)
            if os.name != 'nt':
                self.assertEqual((data / paths.SESSION_TOKEN).stat().st_mode & 0o777, 0o600)
            (data / paths.SESSION_TOKEN).write_text('damaged')
            replaced = paths.session_token(data)
            self.assertNotEqual(replaced, token)
            (data / paths.SESSION_TOKEN).unlink()
            self.assertNotIn(paths.session_token(data), (token, replaced))
            self.assertEqual([p.name for p in data.iterdir()], [paths.SESSION_TOKEN])

    def test_detached_flags(self):
        with ExitStack() as stack:
            for name, value in [('DETACHED_PROCESS', 8), ('CREATE_NEW_PROCESS_GROUP', 512), ('CREATE_NO_WINDOW', 134217728)]:
                stack.enter_context(patch.object(subprocess, name, value, create=True))
            stack.enter_context(patch.object(os, 'name', 'nt'))
            self.assertEqual(paths.detached_options(), {'creationflags': 8 | 512 | 134217728})
        with patch.object(os, 'name', 'posix'):
            self.assertEqual(paths.detached_options(), {'start_new_session': True})

    def test_windows_lock_byte_is_released_on_error(self):
        msvcrt = types.SimpleNamespace(LK_LOCK=1, LK_UNLCK=0, locking=Mock())
        positions = []
        msvcrt.locking.side_effect = lambda fd, mode, count: positions.append((os.lseek(fd, 0, os.SEEK_CUR), mode, count))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'launch.lock'
            with patch.dict(sys.modules, {'msvcrt': msvcrt}), patch.object(os, 'name', 'nt'):
                with self.assertRaisesRegex(RuntimeError, 'exercise'):
                    with paths.file_lock(path):
                        raise RuntimeError('exercise')
                with paths.file_lock(path):
                    pass
            self.assertEqual(path.read_bytes(), b'\0')
        self.assertEqual(positions, [(0, 1, 1), (0, 0, 1)] * 2)

    @unittest.skipIf(os.name == 'nt', 'fcntl is POSIX-only')
    def test_posix_lock_releases_on_error(self):
        import fcntl
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'launch.lock'
            with self.assertRaises(RuntimeError):
                with paths.file_lock(path):
                    with path.open('a+b') as second:
                        with self.assertRaises(BlockingIOError):
                            fcntl.flock(second, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    raise RuntimeError('release')
            with path.open('a+b') as second:
                fcntl.flock(second, fcntl.LOCK_EX | fcntl.LOCK_NB)
                fcntl.flock(second, fcntl.LOCK_UN)


class StopTests(unittest.TestCase):
    def test_pid_commands(self):
        with patch.object(os, 'name', 'posix'):
            self.assertEqual(stop.pid_check_command(321), ['ps', '-p', '321', '-o', 'command='])
        with patch.object(os, 'name', 'nt'):
            command = stop.pid_check_command(321)
            self.assertEqual(command[:4], ['powershell.exe', '-NoProfile', '-NonInteractive', '-Command'])
            self.assertIn('Get-CimInstance Win32_Process -Filter "ProcessId=321"', command[4])
            self.assertTrue(command[4].endswith('.CommandLine'))
        for pid in (0, -1):
            with self.assertRaises(ValueError):stop.pid_check_command(pid)

    def test_only_exact_checkout_script_matches(self):
        script = str(ROOT / 'backend/server.py')
        for platform in ('posix', 'nt'):
            with self.subTest(platform=platform), patch.object(os, 'name', platform):
                for suffix, matches in [('', True), ('.other', False)]:
                    command = f'python "{script}{suffix}" --port 17319'
                    if platform == 'nt':command = command.replace('/', '\\').upper()
                    with patch.object(stop.subprocess, 'run', return_value=types.SimpleNamespace(returncode=0, stdout=command)):
                        self.assertEqual(stop.is_our_server(321), matches)
                with patch.object(stop.subprocess, 'run', return_value=types.SimpleNamespace(returncode=0, stdout='python other/backend/server.py')):
                    self.assertFalse(stop.is_our_server(321))

    def test_windows_query_error_is_not_success(self):
        with patch.object(os, 'name', 'nt'), patch.object(stop.subprocess, 'run', return_value=types.SimpleNamespace(returncode=1)):
            with self.assertRaisesRegex(RuntimeError, 'verify'):stop.is_our_server(321)

    def test_windows_terminate_and_wait(self):
        with patch.object(os, 'name', 'nt'), patch.object(stop.subprocess, 'run') as run, patch.object(stop, 'windows_image', side_effect=['python.exe', None]) as image, patch.object(stop.time, 'sleep'):
            stop.stop_server(321)
        self.assertEqual(run.call_args.args[0], ['taskkill', '/PID', '321', '/T', '/F'])
        self.assertEqual(image.call_count, 2)

    def test_slow_pid_query_obeys_stop_deadline(self):
        with patch.object(os, 'name', 'nt'), patch.object(stop.subprocess, 'run'), patch.object(stop, 'windows_image', side_effect=subprocess.TimeoutExpired('tasklist', 5)) as query, patch.object(stop.time, 'monotonic', side_effect=[0, 1]):
            with self.assertRaisesRegex(RuntimeError, 'within 5 seconds'):stop.stop_server(321)
        query.assert_called_once_with(321, timeout=4)

    def test_windows_slow_query_falls_back_to_tasklist_and_the_session_token(self):
        tasklist = lambda stdout: types.SimpleNamespace(returncode=0, stdout=stdout)
        python_row = '"python.exe","321","Console","1","25,000 K"\n'
        cases = [
            # (PowerShell result, tasklist output, server accepts this folder's token, expected)
            (subprocess.TimeoutExpired('powershell', 20), python_row, True, True),
            (types.SimpleNamespace(returncode=1, stdout=''), python_row, True, True),
            (subprocess.TimeoutExpired('powershell', 20), 'INFO: No tasks are running which match the specified criteria.\n', True, False),
            (subprocess.TimeoutExpired('powershell', 20), '"notepad.exe","321","Console","1","9,000 K"\n', True, False),
            (subprocess.TimeoutExpired('powershell', 20), '"python.exe","3210","Console","1","9,000 K"\n', True, False),
            (subprocess.TimeoutExpired('powershell', 20), python_row, False, RuntimeError),
        ]
        for query, listed, confirms, expected in cases:
            with self.subTest(query=type(query).__name__, listed=listed[:24], confirms=confirms), patch.object(os, 'name', 'nt'), \
                    patch.object(stop.subprocess, 'run', side_effect=[query, tasklist(listed)]) as run, patch.object(stop, 'server_confirms', return_value=confirms):
                if expected is RuntimeError:
                    with self.assertRaisesRegex(RuntimeError, 'verify'):stop.is_our_server(321)
                else:
                    self.assertIs(stop.is_our_server(321), expected)
            self.assertEqual(run.call_args_list[0].kwargs['timeout'], 20)
            self.assertEqual(run.call_args_list[1].args[0], ['tasklist', '/FI', 'PID eq 321', '/FO', 'CSV', '/NH'])

    def test_posix_query_timeout_is_still_an_error(self):
        with patch.object(os, 'name', 'posix'), patch.object(stop.subprocess, 'run', side_effect=subprocess.TimeoutExpired('ps', 20)):
            with self.assertRaises(subprocess.TimeoutExpired):stop.is_our_server(321)

    def test_server_confirms_needs_this_folders_token_and_a_200(self):
        with tempfile.TemporaryDirectory() as directory:
            data = Path(directory)
            response = Mock(status=200)
            response.__enter__ = Mock(return_value=response);response.__exit__ = Mock(return_value=False)
            with patch.object(stop, 'data_dir', return_value=data), patch.object(stop, 'port', return_value=17319), patch.object(stop.urllib.request, 'urlopen', return_value=response) as urlopen:
                self.assertFalse(stop.server_confirms())
                urlopen.assert_not_called()
                token = paths.session_token(data)
                self.assertTrue(stop.server_confirms())
                request = urlopen.call_args.args[0]
                self.assertEqual(request.full_url, 'http://127.0.0.1:17319/api/session')
                self.assertEqual(request.get_header('X-workshop-token'), token)
                urlopen.side_effect = urllib.error.HTTPError(request.full_url, 403, 'Forbidden', {}, None)
                self.assertFalse(stop.server_confirms())

    @unittest.skipIf(os.name == 'nt', 'POSIX signal branch')
    def test_posix_terminate_and_timeout(self):
        with patch.object(stop.os, 'kill') as kill, patch.object(stop, 'is_our_server', return_value=True), patch.object(stop.time, 'monotonic', side_effect=[0, 0, 6]), patch.object(stop.time, 'sleep'):
            with self.assertRaisesRegex(RuntimeError, 'within 5 seconds'):stop.stop_server(321)
        kill.assert_called_once_with(321, signal.SIGTERM)

    def test_unrelated_pid_is_never_killed(self):
        with tempfile.TemporaryDirectory() as directory:
            data = Path(directory)
            (data / 'server.pid').write_text('321')
            with patch.object(stop, 'data_dir', return_value=data), patch.object(stop, 'is_our_server', return_value=False), patch.object(stop, 'stop_server') as terminate:
                stop.main()
            terminate.assert_not_called()
            self.assertTrue((data / 'server.pid').exists())

    def test_timeout_preserves_pid_file(self):
        with tempfile.TemporaryDirectory() as directory:
            data = Path(directory)
            (data / 'server.pid').write_text('321')
            with patch.object(stop, 'data_dir', return_value=data), patch.object(stop, 'is_our_server', return_value=True), patch.object(stop, 'stop_server', side_effect=RuntimeError('timeout')):
                with self.assertRaises(RuntimeError):stop.main()
            self.assertEqual((data / 'server.pid').read_text(), '321')


class LaunchTests(unittest.TestCase):
    def test_missing_files_message_names_the_right_fix(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(launch, 'data_dir', return_value=Path(directory)), patch.object(launch, 'health', return_value=None), patch.object(launch, 'venv_python', return_value=Path(directory) / 'missing'):
                with patch.object(launch, 'installed', return_value=True), self.assertRaisesRegex(RuntimeError, 'Run the install command again'):
                    launch.main()
                with patch.object(launch, 'installed', return_value=False), self.assertRaisesRegex(RuntimeError, 'setup wrapper'):
                    launch.main()

    def test_reuse_and_browser_choice(self):
        with tempfile.TemporaryDirectory() as directory:
            token = paths.session_token(Path(directory))
            umask = os.umask(0o022)
            with patch.object(launch, 'data_dir', return_value=Path(directory)), patch.object(launch, 'port', return_value=17319), patch.object(launch, 'health', return_value={'app': 'ml-workshop', 'version': launch.VERSION}), patch.object(launch, 'token_accepted', return_value=True), patch.object(launch.subprocess, 'Popen') as spawn, patch.object(launch.webbrowser, 'open') as browser:
                try:
                    with patch.object(sys, 'argv', ['launch.py', '--no-open']):launch.main()
                    browser.assert_not_called()
                    with patch.object(sys, 'argv', ['launch.py']):launch.main()
                    # The browser gets the token in the fragment and the user's own umask.
                    browser.assert_called_once_with(f'http://127.0.0.1:17319/#session={token}')
                    if os.name != 'nt':  # Windows keeps no umask bits beyond write protection.
                        self.assertEqual(os.umask(0o022), 0o022)
                finally:
                    os.umask(umask)
                spawn.assert_not_called()

    def test_reuse_needs_this_data_folders_token(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(launch, 'data_dir', return_value=Path(directory)), patch.object(launch, 'port', return_value=17319), patch.object(launch, 'health', return_value={'app': 'ml-workshop'}), patch.object(launch.subprocess, 'Popen') as spawn, patch.object(launch.webbrowser, 'open') as browser:
                with self.assertRaisesRegex(RuntimeError, 'session-token file is missing'):launch.main()
                paths.session_token(Path(directory))
                with patch.object(launch, 'token_accepted', return_value=False), self.assertRaisesRegex(RuntimeError, 'another copy'):launch.main()
            spawn.assert_not_called()
            browser.assert_not_called()

    def test_a_server_from_another_version_is_restarted_when_safe(self):
        old = {'app': 'ml-workshop', 'version': '0.9.0', 'busy': False}
        new = {'app': 'ml-workshop', 'version': launch.VERSION, 'busy': False}
        cases = [
            # (running server, PID verified, this copy has its files, expected error or None)
            (old, True, True, None),
            ({'app': 'ml-workshop'}, True, True, None),
            ({**old, 'busy': True}, True, True, 'is running an exercise'),
            (old, False, True, 'Stop it with the Stop command'),
            (old, True, False, 'needs setup'),
        ]
        for running, verified, files, error in cases:
            with self.subTest(running=running, verified=verified, files=files), tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
                data, root = Path(directory) / 'data', Path(directory) / 'app'
                data.mkdir();(data / 'server.pid').write_text('321');paths.session_token(data)
                if files:(root / 'dist').mkdir(parents=True);(root / 'dist/index.html').write_text('<!doctype html>')
                for name, value in [('data_dir', data), ('port', 17319), ('ROOT', root), ('installed', False), ('token_accepted', True), ('is_our_server', verified)]:
                    stack.enter_context(patch.object(launch, name, **({'new': value} if name == 'ROOT' else {'return_value': value})))
                stack.enter_context(patch.object(launch, 'venv_python', return_value=Path(sys.executable)))
                stack.enter_context(patch.object(launch, 'health', side_effect=[running, new]))
                stop_server = stack.enter_context(patch.object(launch, 'stop_server'))
                spawn = stack.enter_context(patch.object(launch.subprocess, 'Popen'))
                spawn.return_value.poll.return_value = None
                spawn.return_value.pid = 654
                stack.enter_context(patch.object(launch.webbrowser, 'open'))
                stack.enter_context(patch.object(sys, 'argv', ['launch.py', '--no-open']))
                if error:
                    with self.assertRaisesRegex(RuntimeError, error):launch.main()
                    stop_server.assert_not_called();spawn.assert_not_called()
                    self.assertEqual((data / 'server.pid').read_text(), '321')
                else:
                    launch.main()
                    stop_server.assert_called_once_with(321)
                    spawn.assert_called_once()
                    self.assertEqual((data / 'server.pid').read_text(), '654')

    def test_concurrent_launch_api_and_stop(self):
        # CI macOS installs into the selected interpreter; portable CI uses a
        # venv. Both exercise the same real launcher with that interpreter.
        bootstrap = (f'import sys; from pathlib import Path; sys.path.insert(0, {str(ROOT / "scripts")!r}); '
                     'import launch; launch.venv_python=lambda:Path(sys.executable); launch.main()')
        with tempfile.TemporaryDirectory(prefix='workshop-launch-', ignore_cleanup_errors=True) as directory:
            data = Path(directory) / 'data with spaces'
            with socket.socket() as sock:
                sock.bind(('127.0.0.1', 0))
                port = sock.getsockname()[1]
            self.assertNotEqual(port, 7318)
            env = {**os.environ, 'ML_WORKSHOP_DATA_DIR': str(data), 'ML_WORKSHOP_PORT': str(port)}
            command = [sys.executable, '-c', bootstrap, '--no-open']
            stop_command = [sys.executable, str(ROOT / 'scripts/stop.py')]
            try:
                processes = [subprocess.Popen(command, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for _ in range(2)]
                outputs = [process.communicate(timeout=40) for process in processes]
                token = paths.read_session_token(data)
                for process, (stdout, stderr) in zip(processes, outputs):
                    self.assertEqual(process.returncode, 0, stderr)
                    self.assertEqual(stdout.strip(), f'http://127.0.0.1:{port}/#session={token}')
                if os.name != 'nt':
                    for path, mode in [(data, 0o700), (data / 'session-token', 0o600), (data / 'server.log', 0o600), (data / 'workshop.sqlite3', 0o600)]:
                        self.assertEqual(path.stat().st_mode & 0o777, mode, path)
                pid = (data / 'server.pid').read_text()
                subprocess.run(command, cwd=ROOT, env=env, check=True, capture_output=True, timeout=20)
                self.assertEqual((data / 'server.pid').read_text(), pid)
                url = f'http://127.0.0.1:{port}'
                for lesson, code in [('foundations-1', 'print("python works")'), ('web-1', 'console.log("javascript works")')]:
                    request = urllib.request.Request(url + '/api/run', data=json.dumps(dict(lessonId=lesson, code=code, mode='run')).encode(), headers={'Content-Type': 'application/json', 'X-Workshop-Token': token})
                    with urllib.request.urlopen(request, timeout=15) as response:result = json.load(response)
                    self.assertIsNone(result['error'], result)
                    self.assertIn('works', result['stdout'])
                stopped = subprocess.run(stop_command, cwd=ROOT, env=env, capture_output=True, text=True, timeout=20)
                self.assertEqual(stopped.returncode, 0, stopped.stderr)
                self.assertIn('stopped', stopped.stdout)
                self.assertFalse((data / 'server.pid').exists())
                with self.assertRaises(OSError):urllib.request.urlopen(url + '/api/health', timeout=1)
            finally:
                subprocess.run(stop_command, cwd=ROOT, env=env, capture_output=True, timeout=20)


if __name__ == '__main__':unittest.main()
