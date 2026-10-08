"""Stop only the server recorded for this checkout."""
import csv
import os
import re
import signal
import subprocess
import time
import urllib.request

from platform_paths import ROOT, data_dir, file_lock, port, read_session_token

VERIFY_ERROR = 'Could not verify the Engineering Workshop server PID.'
# Get-CimInstance can take more than 5 seconds the first time on a cold Windows computer.
QUERY_TIMEOUT = 20


def pid_check_command(pid):
    if pid <= 0:
        raise ValueError('Invalid server PID.')
    if os.name == 'nt':
        return ['powershell.exe', '-NoProfile', '-NonInteractive', '-Command',
                '[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new(); '
                "$ErrorActionPreference = 'Stop'; "
                f'(Get-CimInstance Win32_Process -Filter "ProcessId={pid}").CommandLine']
    return ['ps', '-p', str(pid), '-o', 'command=']


def is_our_server(pid, timeout=QUERY_TIMEOUT):
    try:
        result = subprocess.run(pid_check_command(pid), capture_output=True, text=True,
                                encoding='utf-8', errors='replace', timeout=timeout)
    except subprocess.TimeoutExpired:
        if os.name != 'nt':
            raise
        return windows_fallback_check(pid)
    # ps returns 1 for a PID which no longer exists. Query failures must not
    # be reported as a successful stop.
    if result.returncode and not (os.name != 'nt' and result.returncode == 1):
        if os.name == 'nt':
            return windows_fallback_check(pid)
        raise RuntimeError(VERIFY_ERROR)
    command = result.stdout.strip()
    script = str(ROOT / 'backend/server.py')
    if os.name == 'nt':
        command = command.replace('/', '\\').casefold()
        script = script.replace('/', '\\').casefold()
    return bool(re.search(r"(?:^|[\s\"'])" + re.escape(script) + r"(?:$|[\s\"'])", command))


def windows_image(pid, timeout=10):
    """Windows only: the image name of a running PID, such as python.exe, or None when no such process runs."""
    result = subprocess.run(['tasklist', '/FI', f'PID eq {pid}', '/FO', 'CSV', '/NH'], capture_output=True,
                            text=True, encoding='utf-8', errors='replace', timeout=timeout)
    if result.returncode:
        raise RuntimeError(VERIFY_ERROR)
    # A match is one CSV row: "python.exe","1234",... Otherwise tasklist prints one INFO line.
    for row in csv.reader(result.stdout.splitlines()):
        if len(row) > 1 and row[1].strip() == str(pid):
            return row[0].strip()
    return None


def server_confirms():
    """True when the server on this copy's port accepts this data folder's session token."""
    token = read_session_token(data_dir())
    if not token:
        return False
    request = urllib.request.Request(f'http://127.0.0.1:{port()}/api/session', headers={'X-Workshop-Token': token})
    try:
        with urllib.request.urlopen(request, timeout=2) as response:
            return response.status == 200
    except OSError:
        return False


def windows_fallback_check(pid):
    """Windows only, when the command-line query fails or times out. The PID from this data folder's
    server.pid must be a Python process, and the server on this copy's port must accept this data
    folder's session token. Anything less is not proof, so it is an error, and nothing is stopped."""
    image = windows_image(pid)
    if image is None:
        return False
    if not image.casefold().startswith('python'):
        return False
    if server_confirms():
        return True
    raise RuntimeError(VERIFY_ERROR)


def still_running(pid, timeout):
    """After a stop request: whether the PID, already checked as this server, is still running."""
    if os.name == 'nt':
        # tasklist answers quickly; Get-CimInstance can be slow.
        return windows_image(pid, timeout=timeout) is not None
    return is_our_server(pid, timeout=timeout)


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
            if not still_running(pid, timeout=remaining):
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
