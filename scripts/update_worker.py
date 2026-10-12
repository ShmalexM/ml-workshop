"""Detached installed-app update coordinator. Only stdlib; copied outside app/ before use."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import urllib.request

VERSION_PATTERN = re.compile(r'(0|[1-9][0-9]{0,5})\.(0|[1-9][0-9]{0,5})\.(0|[1-9][0-9]{0,5})')
ACTIVE = {'updating', 'restarting'}


class InstallerBusy(RuntimeError):
    pass


def process_alive(pid):
    if type(pid) is not int or pid <= 0:
        return False
    if os.name == 'nt':
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
        kernel.GetExitCodeProcess.argtypes = (wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD))
        kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
        handle = kernel.OpenProcess(0x1000, False, pid)
        if not handle:
            return False
        try:
            code = wintypes.DWORD()
            return bool(kernel.GetExitCodeProcess(handle, ctypes.byref(code))) and code.value == 259
        finally:
            kernel.CloseHandle(handle)
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


@contextmanager
def install_lock(install):
    lock = Path(install) / '.install-lock'
    try:
        lock.mkdir(mode=0o700)
    except FileExistsError:
        try:
            pid = int((lock / 'pid').read_text())
        except (OSError, ValueError):
            raise InstallerBusy('Another installer is starting.') from None
        if process_alive(pid):
            raise InstallerBusy('Another installer is running.')
        (lock / 'pid').unlink()
        lock.rmdir()
        lock.mkdir(mode=0o700)
    (lock / 'pid').write_text(str(os.getpid()))
    try:
        yield
    finally:
        if (lock / 'pid').read_text() == str(os.getpid()):
            (lock / 'pid').unlink()
            lock.rmdir()


def valid_version(value):
    return isinstance(value, str) and VERSION_PATTERN.fullmatch(value) is not None


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def read_status(data):
    try:
        value = json.loads((Path(data) / 'update-status.json').read_text(encoding='utf-8'))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError, RecursionError):
        return {}


def write_status(data, **changes):
    target = Path(data) / 'update-status.json'
    current = read_status(data)
    current.update(changes)
    temporary = target.with_name(f'.update-status-{os.getpid()}.tmp')
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, 'w', encoding='utf-8') as stream:
        json.dump(current, stream)
    os.replace(temporary, target)


@contextmanager
def worker_lock(data):
    with (Path(data) / 'update-worker.lock').open('a+b') as lock:
        if os.name == 'nt':
            import msvcrt
            lock.write(b'\0'); lock.flush(); lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            if os.name == 'nt':
                lock.seek(0); msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(lock, fcntl.LOCK_UN)


def detached_options():
    if os.name == 'nt':
        return dict(creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW)
    return dict(start_new_session=True)


def wait_bootstrap_exit(pid):
    if os.name == 'nt':
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
        kernel.WaitForSingleObject.argtypes = (wintypes.HANDLE, wintypes.DWORD)
        kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
        handle = kernel.OpenProcess(0x100000, False, pid)
        if not handle:
            return
        try:
            if kernel.WaitForSingleObject(handle, 10000) != 0:
                raise RuntimeError('bootstrap did not exit')
        finally:
            kernel.CloseHandle(handle)
        return
    for _ in range(100):
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return
        time.sleep(.1)
    raise RuntimeError('bootstrap did not exit')


def installer_command(installer, platform=None):
    if (platform or sys.platform) == 'win32':
        return ['powershell.exe', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-File', str(installer)]
    return ['/bin/sh', str(installer)]


def run_installer(command, install, env, log):
    process = subprocess.Popen(command, cwd=install, env=env, stdin=subprocess.DEVNULL,
                               stdout=log, stderr=log, **detached_options())
    try:
        return process.wait(timeout=5400)
    except subprocess.TimeoutExpired:
        if os.name == 'nt':
            subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'], stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, timeout=10)
        else:
            import signal
            os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=10)
        raise


def installer_environment(install, data, port, target, light):
    # Do not inherit EW_ARCHIVE, Python injection variables, provider credentials or arbitrary installer options.
    allowed = ('PATH', 'HOME', 'LANG', 'SYSTEMROOT', 'WINDIR', 'USERPROFILE', 'LOCALAPPDATA', 'TEMP', 'TMP',
               'PROCESSOR_ARCHITECTURE', 'PROCESSOR_ARCHITEW6432')
    env = {key: os.environ[key] for key in allowed if key in os.environ}
    env.update(EW_HOME=str(install), EW_RELEASE_TAG='v' + target, EW_KEEP_OLD='1', EW_NO_LAUNCH='1',
               EW_NO_SHORTCUTS='1', EW_LIGHT='1' if light else '0', EW_LOCK_PID=str(os.getpid()),
               EW_REQUIRE_ML='0' if light else '1',
               ML_WORKSHOP_DATA_DIR=str(data), ML_WORKSHOP_PORT=str(port))
    return env


def app_python(app):
    return app / '.venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')


def restart(install, env):
    app = install / 'app'
    # launch.py inherits the same data folder and port. Add the installed Node runtime explicitly.
    node = install / 'runtime/node'
    if os.name != 'nt':
        node = node / 'bin'
    env = dict(env, PATH=os.pathsep.join(filter(None, (str(node), env.get('PATH')))))
    result = subprocess.run([str(app_python(app)), str(app / 'scripts/launch.py'), '--no-open'],
                            cwd=install, env=env, stdin=subprocess.DEVNULL,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=35)
    if result.returncode:
        raise RuntimeError('restart')


def healthy(port, data, expected):
    token = (data / 'session-token').read_text(encoding='ascii').strip()
    base = f'http://127.0.0.1:{port}'
    with urllib.request.urlopen(base + '/api/health', timeout=2) as response:
        status = json.load(response)
    if status.get('app') != 'ml-workshop' or status.get('version') != expected:
        return False
    request = urllib.request.Request(base + '/api/session', headers={'X-Workshop-Token': token})
    with urllib.request.urlopen(request, timeout=2) as response:
        return response.status == 200


def wait_healthy(port, data, expected):
    for _ in range(30):
        try:
            if healthy(port, data, expected):
                return True
        except (OSError, ValueError):
            pass
        time.sleep(.2)
    return False


def rollback(install, data, port, previous, env):
    old = install / '.app-old'
    app = install / 'app'
    if old.is_dir():
        # Stop only the app recorded in this install's data folder before moving a failed replacement.
        if app.exists():
            stop = subprocess.run([str(app_python(app)), str(app / 'scripts/stop.py')], cwd=install, env=env,
                                  stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=35)
            if stop.returncode:
                return False
        failed = install / '.app-failed'
        if failed.exists():
            shutil.rmtree(failed)
        if app.exists():
            app.rename(failed)
        old.rename(app)
    restart(install, env)
    return wait_healthy(port, data, previous)


def run_update(install, data, port, target, previous, light):
    install, data = Path(install).resolve(), Path(data).resolve()
    if not valid_version(target) or not valid_version(previous) or not 1 <= port <= 65535:
        raise ValueError('Invalid update request.')
    if not (install / '.engineering-workshop').is_file() or data != install / 'data':
        raise ValueError('Only marked standard installations support in-app updates.')
    with worker_lock(data):
        try:
            with install_lock(install):
                perform_update(install, data, port, target, previous, light)
        except InstallerBusy:
            message = 'Another installer is running. Wait for it to finish, then try again.'
            write_status(data, status='error', phase=message, error=message)


def perform_update(install, data, port, target, previous, light):
    write_status(data, status='updating', phase='Downloading, verifying and installing the release; this may take a few minutes.',
                 pid=os.getpid(), startedAt=timestamp(), error=None)
    env = installer_environment(install, data, port, target, light)
    extension = 'ps1' if os.name == 'nt' else 'sh'
    installer = data / 'update-work' / ('install.' + extension)
    try:
        with (data / 'update.log').open('ab') as log:
            result = run_installer(installer_command(installer), install, env, log)
        if result:
            raise RuntimeError('install')
        write_status(data, status='restarting', phase='Restarting Engineering Workshop.', error=None)
        restart(install, env)
        if not wait_healthy(port, data, target):
            raise RuntimeError('health')
        write_status(data, status='updated', phase='Update complete. Your saved work is ready.', error=None,
                     latestVersion=target, finishedAt=timestamp())
        old = install / '.app-old'
        if old.is_dir():
            shutil.rmtree(old, ignore_errors=True)
    except Exception:
        try:
            restored = rollback(install, data, port, previous, env)
        except Exception:
            restored = False
        message = ('The update could not finish. Your previous version is running and your saved work is kept. Try again.'
                   if restored else 'The update could not finish. Your saved work is kept. Open the app again, or rerun the install command.')
        write_status(data, status='error', phase=message, error=message, finishedAt=timestamp())

def bootstrap(arguments):
    """Exit before the installer stops the server, so taskkill /T cannot find this worker below it."""
    process = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), *arguments, '--bootstrap-pid', str(os.getpid())],
                               cwd=Path(arguments[arguments.index('--install') + 1]),
                               stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                               **detached_options())
    print(process.pid, flush=True)


def main():
    if '--bootstrap' in sys.argv:
        bootstrap([argument for argument in sys.argv[1:] if argument != '--bootstrap'])
        return
    parser = argparse.ArgumentParser()
    parser.add_argument('--install', required=True)
    parser.add_argument('--data', required=True)
    parser.add_argument('--port', required=True, type=int)
    parser.add_argument('--target', required=True)
    parser.add_argument('--previous', required=True)
    parser.add_argument('--light', action='store_true')
    parser.add_argument('--bootstrap-pid', type=int)
    args = parser.parse_args()
    if args.bootstrap_pid:
        wait_bootstrap_exit(args.bootstrap_pid)
    run_update(args.install, args.data, args.port, args.target, args.previous, args.light)


if __name__ == '__main__':
    main()
