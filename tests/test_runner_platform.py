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
    def test_posix_limits_unchanged(self):
        import resource
        with patch.object(resource, 'setrlimit') as limit:
            runner.apply_limits()
        self.assertEqual(limit.call_args_list[0].args, (resource.RLIMIT_CPU, (40, 45)))
        self.assertEqual(limit.call_args_list[1].args, (resource.RLIMIT_FSIZE, (1024 * 1024, 1024 * 1024)))

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
                cleanup.assert_called_once_with(process)

    def test_windows_cleanup_command_and_kill_fallback(self):
        process = Mock(pid=123)
        process.poll.return_value = None
        with patch.object(sys, 'platform', 'win32'), patch.object(runner.subprocess, 'run') as run:
            runner.cleanup_process(process)
        self.assertEqual(run.call_args.args[0], ['taskkill', '/T', '/F', '/PID', '123'])
        process.kill.assert_called_once()
        process.wait.assert_called_once()

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


if __name__ == '__main__':unittest.main()
