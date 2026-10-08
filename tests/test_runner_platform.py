"""Execution limits, Windows dispatch, environment isolation, and tree cleanup."""
from contextlib import ExitStack
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import types
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
import runner


class RunnerPlatformTests(unittest.TestCase):
    def test_windows_skips_resource_limits(self):
        with patch.object(sys, 'platform', 'win32'), patch.object(runner, 'resource') as limits:
            runner.apply_limits()
            limits.setrlimit.assert_not_called()
        with patch.object(runner, 'resource', None):runner.apply_limits()

    @unittest.skipIf(os.name == 'nt', 'POSIX resource limits')
    def test_posix_limits(self):
        import resource
        infinity = resource.RLIM_INFINITY
        for count, current, expected in [(100, (infinity, infinity), 356), (100, (300, infinity), 300), (100, (infinity, 200), 200), (None, (infinity, infinity), None)]:
            with self.subTest(count=count, current=current), patch.object(resource, 'setrlimit') as limit, \
                    patch.object(runner, 'user_process_count', return_value=count), patch.object(resource, 'getrlimit', return_value=current):
                runner.apply_limits()
            self.assertEqual(limit.call_args_list[0].args, (resource.RLIMIT_CPU, (40, 45)))
            self.assertEqual(limit.call_args_list[1].args, (resource.RLIMIT_FSIZE, (1024 * 1024, 1024 * 1024)))
            nproc = [call.args[1] for call in limit.call_args_list if call.args[0] == resource.RLIMIT_NPROC]
            self.assertEqual(nproc, [] if expected is None else [(expected, expected)])

    @unittest.skipIf(os.name == 'nt', 'POSIX resource limits')
    def test_memory_limit_on_linux_only(self):
        import resource
        infinity = resource.RLIM_INFINITY
        for platform, current, expected in [('linux', infinity, [(4 << 30, 4 << 30)]), ('linux', 1 << 30, [(1 << 30, 1 << 30)]), ('darwin', infinity, [])]:
            with self.subTest(platform=platform, current=current), patch.object(sys, 'platform', platform), patch.object(resource, 'setrlimit') as limit, \
                    patch.object(runner, 'user_process_count', return_value=None), patch.object(resource, 'getrlimit', return_value=(current, current)):
                runner.apply_limits()
            self.assertEqual([call.args[1] for call in limit.call_args_list if call.args[0] == resource.RLIMIT_DATA], expected)

    @unittest.skipUnless(sys.platform == 'darwin' or sys.platform.startswith('linux'), 'process count on macOS and Linux')
    def test_process_limit_is_above_the_users_current_count(self):
        import resource
        count = runner.user_process_count()
        self.assertGreater(count, 1)
        result = runner.execute('import resource; print(*resource.getrlimit(resource.RLIMIT_NPROC))', [])
        soft, hard = map(int, result['stdout'].split())
        self.assertEqual(soft, hard)
        system = resource.getrlimit(resource.RLIMIT_NPROC)[0]
        self.assertGreaterEqual(soft, min(count + 100, system if system != resource.RLIM_INFINITY else soft))
        self.assertLessEqual(soft, count + runner.EXTRA_PROCESSES + 100)

    def test_windows_direct_node_and_minimal_environment(self):
        for language in ('python', 'javascript'):
            with self.subTest(language=language), ExitStack() as stack:
                stack.enter_context(patch.object(sys, 'platform', 'win32'))
                stack.enter_context(patch.object(subprocess, 'CREATE_NEW_PROCESS_GROUP', 512, create=True))
                stack.enter_context(patch.object(runner, 'node_binary', return_value='node.exe'))
                stack.enter_context(patch.dict(os.environ, {'SYSTEMROOT': 'C:\\Windows', 'TEMP': 'temp', 'TMP': 'tmp', 'PATHEXT': '.EXE', 'WINDIR': 'C:\\Windows', 'USERPROFILE': 'profile', 'OPENAI_API_KEY': 'secret', 'ML_WORKSHOP_TOKEN': 'secret', 'ML_WORKSHOP_DATA_DIR': 'private'}, clear=True))
                process = Mock(pid=123, returncode=0)
                process.poll.return_value = 0
                spawn = stack.enter_context(patch.object(runner.subprocess, 'Popen', return_value=process))
                def finish(proc, result, timeout):
                    result.write_text(json.dumps(dict(error=None, checks=[], passed=False)))
                stack.enter_context(patch.object(runner, 'wait_for_result', side_effect=finish))
                cleanup = stack.enter_context(patch.object(runner, 'cleanup_process'))
                result = runner.execute('print(1)', [], language=language)
                self.assertIsNone(result['error'])
                arguments = spawn.call_args.args[0]
                if language == 'javascript':
                    self.assertEqual(arguments[0], 'node.exe')
                    self.assertTrue(arguments[1].endswith('js_runner.cjs'))
                    self.assertEqual(len(arguments), 4)
                else:
                    self.assertEqual(arguments[:4], [sys.executable, '-I', '-X', 'utf8'])
                options = spawn.call_args.kwargs
                self.assertEqual(options['creationflags'], 512)
                self.assertNotIn('start_new_session', options)
                for name in ('OPENAI_API_KEY', 'ML_WORKSHOP_TOKEN', 'ML_WORKSHOP_DATA_DIR'):
                    self.assertNotIn(name, options['env'])
                for name in ('SYSTEMROOT', 'TEMP', 'TMP', 'PATHEXT', 'WINDIR', 'USERPROFILE'):
                    self.assertIn(name, options['env'])
                cleanup.assert_called_once()
                self.assertIs(cleanup.call_args.args[0], process)
                # Temporary files go in the exercise folder.
                for name in ('TEMP', 'TMP', 'TMPDIR'):
                    self.assertEqual(options['env'][name], str(options['cwd']))

    def test_windows_cleanup_command_and_kill_fallback(self):
        process = Mock(pid=123)
        process.poll.return_value = None
        with patch.object(sys, 'platform', 'win32'), patch.object(runner.subprocess, 'run') as run:
            runner.cleanup_process(process)
        self.assertEqual(run.call_args.args[0], ['taskkill', '/T', '/F', '/PID', '123'])
        process.kill.assert_called_once()
        process.wait.assert_called_once()

    def test_windows_result_read_waits_for_a_locked_file(self):
        with tempfile.TemporaryDirectory() as directory:
            result = Path(directory) / 'result.json'
            result.write_text('{"passed": true}')
            read = Path.read_text
            attempts = []
            def locked(path, *args, **kwargs):
                attempts.append(path)
                if len(attempts) < 3:raise PermissionError(13, 'Permission denied', str(path))
                return read(path, *args, **kwargs)
            with patch.object(sys, 'platform', 'win32'), patch.object(Path, 'read_text', autospec=True, side_effect=locked), patch.object(time, 'sleep'):
                self.assertEqual(runner.read_result(result), {'passed': True})
            self.assertEqual(len(attempts), 3)
            # Elsewhere, and after 1 second on Windows, the error is raised.
            with patch.object(sys, 'platform', 'linux'), patch.object(Path, 'read_text', side_effect=PermissionError(13, 'denied')):
                with self.assertRaises(PermissionError):runner.read_result(result)
            with patch.object(sys, 'platform', 'win32'), patch.object(Path, 'read_text', side_effect=PermissionError(13, 'denied')), \
                    patch.object(time, 'monotonic', side_effect=[0, 0.5, 1.1]), patch.object(time, 'sleep'):
                with self.assertRaises(PermissionError):runner.read_result(result)

    @unittest.skipUnless(sys.platform.startswith('linux'), 'memory limit on Linux')
    def test_runaway_allocation_raises_memory_error_on_linux(self):
        result = runner.execute('data = bytearray(6 << 30)', [])
        self.assertIn('MemoryError', result['error'] or '', result)

    def test_temporary_files_go_in_the_exercise_folder(self):
        result = runner.execute('import os, tempfile; print(os.path.realpath(tempfile.gettempdir()) == os.path.realpath(os.getcwd()))', [])
        self.assertEqual(result['stdout'].strip(), 'True', result)

    @unittest.skipIf(os.name == 'nt', 'POSIX wait')
    def test_posix_wait_returns_at_the_exit_and_stops_at_the_timeout(self):
        with tempfile.TemporaryDirectory() as directory:
            result = Path(directory) / 'result.json'
            quick = subprocess.Popen([sys.executable, '-c', 'pass'])
            runner.wait_for_result(quick, result, 30)
            self.assertEqual(quick.returncode, 0)
            slow = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'])
            try:
                started = time.monotonic()
                with self.assertRaises(subprocess.TimeoutExpired):runner.wait_for_result(slow, result, .3)
                self.assertLess(time.monotonic() - started, 10)
                self.assertIsNone(slow.returncode)
            finally:
                slow.kill()
                slow.wait()
            self.assertIsNotNone(slow.returncode)

    def test_exercise_process_skips_the_server_only_modules(self):
        # The exercise process runs runner.py as a script and must not need what only the server uses.
        with tempfile.TemporaryDirectory() as directory:
            request, result = Path(directory) / 'request.json', Path(directory) / 'result.json'
            request.write_text(json.dumps(dict(code='import sys; print(sorted(m for m in ("secrets", "tempfile", "threading") if m in sys.modules))', checks=[])))
            out = subprocess.run([sys.executable, '-I', '-X', 'utf8', runner.__file__, str(request), str(result)], cwd=directory,
                                 capture_output=True, text=True, timeout=60)
            self.assertEqual(out.returncode, 0, out.stderr)
            self.assertIsNone(json.loads(result.read_text())['error'])
            self.assertEqual(out.stdout.strip(), '[]')

    def test_windows_wall_timeout(self):
        with tempfile.TemporaryDirectory() as directory:
            result = Path(directory) / 'result.json'
            process = Mock(args=['python'])
            process.poll.return_value = None
            with patch.object(sys, 'platform', 'win32'), patch.object(time, 'monotonic', side_effect=[0, 2]):
                with self.assertRaises(subprocess.TimeoutExpired):runner.wait_for_result(process, result, 1)

    def test_node_fallback_paths(self):
        for platform, expected in [('linux', str(Path('/usr/bin/node'))), ('win32', str(Path('/program files') / 'nodejs/node.exe'))]:
            with self.subTest(platform=platform), patch.object(sys, 'platform', platform), patch.dict(os.environ, {'ProgramFiles': '/program files'}), patch.object(runner.shutil, 'which', return_value=None), patch.object(Path, 'is_file', autospec=True, side_effect=lambda p: str(p) == expected), patch.object(runner.os, 'access', return_value=True):
                self.assertEqual(runner.node_binary(), str(Path(expected).resolve()))

    def test_missing_package_message_in_code_and_checks(self):
        result = runner.execute('import workshop_missing_fixture_package', [])
        self.assertIn("Missing Python module 'workshop_missing_fixture_package'", result['error'])
        self.assertIn('Run the install command again', result['error'])
        self.assertIn('without --no-ml', result['error'])
        result = runner.execute('', [{'label': 'import', 'expr': '__import__("workshop_missing_fixture_package")'}])
        self.assertFalse(result['passed'])
        self.assertIn('without --no-ml', result['checks'][0]['detail'])

    def test_unicode_stdout_and_output_cap(self):
        for language, code in [('python', 'print("café → test")'), ('javascript', 'console.log("café → test")')]:
            with self.subTest(language=language):
                result = runner.execute(code, [], language=language)
                self.assertIsNone(result['error'], result)
                self.assertEqual(result['stdout'].strip(), 'café → test')
        result = runner.execute('print("x" * 25000)', [])
        self.assertTrue(result['stdout'].endswith('[Output truncated]'))

    def test_runner_does_not_inherit_secrets(self):
        with patch.dict(os.environ, {'WORKSHOP_TEST_SECRET': 'private', 'ML_WORKSHOP_TOKEN': 'private'}):
            result = runner.execute('import os; print(os.getenv("WORKSHOP_TEST_SECRET")); print(os.getenv("ML_WORKSHOP_TOKEN"))', [])
        self.assertEqual(result['stdout'].strip(), 'None\nNone')

    def test_descendants_cleaned_after_completion_and_timeout(self):
        for language in ('python', 'javascript'):
            for timeout in (False, True):
                with self.subTest(language=language, timeout=timeout), tempfile.TemporaryDirectory() as directory:
                    started = Path(directory) / 'started'
                    survived = Path(directory) / 'survived'
                    if language == 'python':
                        child = f'from pathlib import Path; import time; Path({str(started)!r}).touch(); time.sleep(2); Path({str(survived)!r}).touch()'
                        code = (f'import subprocess, sys, time; from pathlib import Path\nsubprocess.Popen([sys.executable, "-c", {child!r}])\n'
                                f'while not Path({str(started)!r}).exists(): time.sleep(.01)\n')
                        if timeout:code += 'time.sleep(30)\n'
                    else:
                        child = f'const fs=require("node:fs");fs.writeFileSync({json.dumps(str(started))}, "");setTimeout(()=>fs.writeFileSync({json.dumps(str(survived))}, ""),2000);'
                        code = (f'require("node:child_process").spawn(process.execPath,["-e",{json.dumps(child)}],{{stdio:"ignore"}}).unref();'
                                f'while(!require("node:fs").existsSync({json.dumps(str(started))})){{}}')
                        if timeout:code += 'while(true){}'
                    result = runner.execute(code, [], timeout=1 if timeout else 10, language=language)
                    self.assertTrue(started.exists(), result)
                    if timeout:self.assertIn('Execution stopped', result['error'])
                    else:self.assertIsNone(result['error'], result)
                    time.sleep(2.1)
                    self.assertFalse(survived.exists(), 'An exercise child survived cleanup')


def alive(pid):
    """True while the process exists and is not a zombie."""
    if sys.platform.startswith('linux'):
        try:return Path(f'/proc/{pid}/stat').read_text().split(') ', 1)[1][0] != 'Z'
        except OSError:return False
    state = subprocess.run(['ps', '-o', 'stat=', '-p', str(pid)], capture_output=True, text=True).stdout.strip()
    return bool(state) and not state.startswith('Z')


@unittest.skipIf(os.name == 'nt', 'Windows ends the process tree with taskkill /T')
class SessionLeaverTests(unittest.TestCase):
    """Children that call setsid() leave the exercise's process group. Cleanup still finds them."""
    def gone(self, pids):
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline and any(alive(pid) for pid in pids):time.sleep(.05)
        return [pid for pid in pids if alive(pid)]

    def test_grandchildren_in_new_sessions_are_killed_after_finish_and_timeout(self):
        python = (f'import os, subprocess, sys, time\n'
                  # A new session in the exercise folder, one that leaves the folder, and a system shell that does both.
                  f'children = [subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"], start_new_session=True),\n'
                  f'            subprocess.Popen([sys.executable, "-c", "import os, time; os.chdir(os.sep); time.sleep(60)"], start_new_session=True,\n'
                  f'                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL),\n'
                  f'            subprocess.Popen(["/bin/sh", "-c", "cd /; sleep 60 & echo $!; wait"], start_new_session=True, stdout=subprocess.PIPE)]\n'
                  f'print(*[child.pid for child in children], children[2].stdout.readline().decode().strip(), flush=True)\n')
        javascript = ('const {spawn} = require("node:child_process");'
                      'const child = spawn(process.execPath, ["-e", "setTimeout(() => {}, 60000)"], {detached: true, stdio: "inherit"}); child.unref();'
                      'console.log(child.pid);')
        for language, code in [('python', python), ('javascript', javascript)]:
            for timeout in (False, True):
                with self.subTest(language=language, timeout=timeout):
                    if timeout:code += 'time.sleep(30)\n' if language == 'python' else 'while(true){}'
                    result = runner.execute(code, [], timeout=3 if timeout else 20, language=language)
                    pids = [int(pid) for pid in result['stdout'].split()]
                    self.assertEqual(len(pids), 4 if language == 'python' else 1, result)
                    if timeout:self.assertIn('Execution stopped', result['error'])
                    else:self.assertIsNone(result['error'], result)
                    self.assertEqual(self.gone(pids), [], 'An exercise process survived cleanup')

    def test_process_limit_stops_a_fork_loop_and_cleanup_ends_every_process(self):
        code = ('import subprocess\nstarted = []\n'
                'try:\n'
                '    for _ in range(5000):started.append(subprocess.Popen(["sleep", "60"], start_new_session=True))\n'
                'except OSError:pass\n'
                'print(*[process.pid for process in started])\n')
        result = runner.execute(code, [])
        pids = [int(pid) for pid in result['stdout'].split()]
        self.assertIsNone(result['error'], result)
        self.assertGreater(len(pids), 10)
        self.assertLess(len(pids), runner.EXTRA_PROCESSES + 100)
        self.assertEqual(self.gone(pids), [], 'An exercise process survived cleanup')


if __name__ == '__main__':unittest.main()
