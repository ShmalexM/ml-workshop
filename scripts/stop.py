"""Stop only the server recorded for this checkout."""
import os
import re
import signal
import subprocess
import time

from platform_paths import ROOT, data_dir, file_lock


def pid_check_command(pid):
    if pid <= 0:
        raise ValueError('Invalid server PID.')
    if os.name == 'nt':
        return ['powershell.exe', '-NoProfile', '-NonInteractive', '-Command',
                '[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new(); '
                "$ErrorActionPreference = 'Stop'; "
                f'(Get-CimInstance Win32_Process -Filter "ProcessId={pid}").CommandLine']
    return ['ps', '-p', str(pid), '-o', 'command=']


def is_our_server(pid, timeout=5):
    result = subprocess.run(pid_check_command(pid), capture_output=True, text=True,
                            encoding='utf-8', errors='replace', timeout=timeout)
    # ps returns 1 for a PID which no longer exists. Query failures must not
    # be reported as a successful stop.
    if result.returncode and not (os.name != 'nt' and result.returncode == 1):
        raise RuntimeError('Could not verify the Engineering Workshop server PID.')
    command = result.stdout.strip()
    script = str(ROOT / 'backend/server.py')
    if os.name == 'nt':
        command = command.replace('/', '\\').casefold()
        script = script.replace('/', '\\').casefold()
    return bool(re.search(r"(?:^|[\s\"'])" + re.escape(script) + r"(?:$|[\s\"'])", command))


def stop_server(pid):
    if os.name == 'nt':
        subprocess.run(['taskkill', '/PID', str(pid), '/T', '/F'],
                       capture_output=True, check=True, timeout=5)
    else:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            return
    deadline = time.monotonic() + 5
    while (remaining := deadline - time.monotonic()) > 0:
        try:
            if not is_our_server(pid, timeout=remaining):
                return
        except subprocess.TimeoutExpired:
            break
        time.sleep(min(.1, remaining))
    raise RuntimeError('Engineering Workshop did not stop within 5 seconds. Its PID file was kept.')


def main():
    data = data_dir()
    pid_file = data / 'server.pid'
    if not pid_file.exists():
        print('Engineering Workshop is already stopped.')
        return
    with file_lock(data / 'launch.lock'):
        if not pid_file.exists():
            print('Engineering Workshop is already stopped.')
            return
        pid = int(pid_file.read_text())
        if not is_our_server(pid):
            print('No matching Engineering Workshop process is running.')
            return
        stop_server(pid)
        pid_file.unlink(missing_ok=True)
    print('Engineering Workshop stopped. Your progress is saved.')


if __name__ == '__main__':
    main()
