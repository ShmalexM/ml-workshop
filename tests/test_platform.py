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
        with patch.object(os, 'name', 'nt'), patch.object(stop.subprocess, 'run') as run, patch.object(stop, 'is_our_server', side_effect=[True, False]), patch.object(stop.time, 'sleep'):
            stop.stop_server(321)
        self.assertEqual(run.call_args.args[0], ['taskkill', '/PID', '321', '/T', '/F'])

    def test_slow_pid_query_obeys_stop_deadline(self):
        with patch.object(os, 'name', 'nt'), patch.object(stop.subprocess, 'run'), patch.object(stop, 'is_our_server', side_effect=subprocess.TimeoutExpired('powershell', 5)) as query, patch.object(stop.time, 'monotonic', side_effect=[0, 1]):
            with self.assertRaisesRegex(RuntimeError, 'within 5 seconds'):stop.stop_server(321)
        query.assert_called_once_with(321, timeout=4)

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
    def test_reuse_and_browser_choice(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(launch, 'data_dir', return_value=Path(directory)), patch.object(launch, 'port', return_value=17319), patch.object(launch, 'health', return_value={'app': 'ml-workshop'}), patch.object(launch.subprocess, 'Popen') as spawn, patch.object(launch.webbrowser, 'open') as browser:
                with patch.object(sys, 'argv', ['launch.py', '--no-open']):launch.main()
                browser.assert_not_called()
                with patch.object(sys, 'argv', ['launch.py']):launch.main()
                browser.assert_called_once_with('http://127.0.0.1:17319')
                spawn.assert_not_called()

    def test_concurrent_launch_api_and_stop(self):
        # CI macOS installs into the selected interpreter; portable CI uses a
        # venv. Both exercise the same real launcher with that interpreter.
        bootstrap = (f'import sys; from pathlib import Path; sys.path.insert(0, {str(ROOT / "scripts")!r}); '
                     'import launch; launch.venv_python=lambda:Path(sys.executable); launch.main()')
        with tempfile.TemporaryDirectory(prefix='workshop-launch-') as directory:
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
                for process in processes:
                    stdout, stderr = process.communicate(timeout=40)
                    self.assertEqual(process.returncode, 0, stderr)
                    self.assertEqual(stdout.strip(), f'http://127.0.0.1:{port}')
                pid = (data / 'server.pid').read_text()
                subprocess.run(command, cwd=ROOT, env=env, check=True, capture_output=True, timeout=20)
                self.assertEqual((data / 'server.pid').read_text(), pid)
                url = f'http://127.0.0.1:{port}'
                with urllib.request.urlopen(url + '/api/bootstrap') as response:
                    token = json.load(response)['token']
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
