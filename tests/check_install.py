"""Check a copy made by install.sh or install.ps1.

Checks that the build includes the open-source license list, starts the app on a free
port without opening a browser, checks /api/health, runs one Python and one JavaScript
exercise, then stops it. CI runs this after the installer.

Usage: python tests/check_install.py <install folder>
"""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import urllib.request


def check(condition, message):
    if not condition:
        raise SystemExit(f'Check failed: {message}')


def call(url, data=None, token=None):
    headers = {'Content-Type': 'application/json', 'X-Workshop-Token': token} if data else {}
    request = urllib.request.Request(url, data=json.dumps(data).encode() if data else None, headers=headers)
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def main(install):
    install = Path(install).resolve()
    licenses = install / 'app' / 'dist' / 'THIRD_PARTY_LICENSES.txt'
    check(licenses.is_file() and 'react' in licenses.read_text(encoding='utf-8'), f'{licenses} is missing or does not list react')
    python = install / 'app' / '.venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    command = [str(python), str(install / 'app' / 'scripts' / 'installed.py')]
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    env = {**os.environ, 'ML_WORKSHOP_PORT': str(port)}
    url = f'http://127.0.0.1:{port}'
    try:
        started = subprocess.run(command + ['--no-open'], env=env, capture_output=True, text=True, timeout=120)
        check(started.returncode == 0, f'the app did not start: {started.stderr}')
        check(started.stdout.strip() == url, f'unexpected launcher output: {started.stdout!r}')
        health = call(url + '/api/health')
        check(health.get('app') == 'ml-workshop', f'unexpected /api/health response: {health}')
        print(f'{url}/api/health -> {health}')
        token = call(url + '/api/bootstrap')['token']
        for lesson, code in [('foundations-1', 'print("python works")'), ('web-1', 'console.log("javascript works")')]:
            result = call(url + '/api/run', dict(lessonId=lesson, code=code, mode='run'), token)
            check(result.get('error') is None and 'works' in result.get('stdout', ''), f'{lesson}: {result}')
            print(f'{lesson}: {result["stdout"].strip()}')
    finally:
        stopped = subprocess.run(command + ['--stop'], env=env, capture_output=True, text=True, timeout=60)
    check(stopped.returncode == 0 and 'stopped' in stopped.stdout, f'the app did not stop: {stopped}')
    check((install / 'data' / 'workshop.sqlite3').is_file(), 'no progress database in the data folder')
    print('The installed app starts, runs Python and JavaScript exercises, and stops.')


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    main(sys.argv[1])
