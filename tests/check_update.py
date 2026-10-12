"""CI-only real in-app update check for a disposable one-line installation.

Usage: <stable runtime Python> tests/check_update.py <install folder> <candidate archive>

The installed version is lowered only in the disposable fixture. Its copied worker
gets the local candidate archive through a fixture-only environment patch; the
production HTTP API still receives exactly {}. Everything after that is real:
orphan bootstrap, native installer, checksum verification, process stop and restart.
"""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request


def check(condition, message):
    if not condition:
        raise RuntimeError(message)


def call(base, path, token=None, body=None):
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['X-Workshop-Token'] = token
    request = urllib.request.Request(base + path, data=json.dumps(body).encode() if body is not None else None,
                                     headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def atomic_bytes(path, value):
    temporary = path.with_name(path.name + '.tmp-ci-update')
    temporary.write_bytes(value)
    temporary.replace(path)


def previous_version(version):
    check(re.fullmatch(r'(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)', version), 'Candidate must have a stable numeric version.')
    major, minor, patch = map(int, version.split('.'))
    if patch:
        return f'{major}.{minor}.{patch - 1}'
    if minor:
        return f'{major}.{minor - 1}.0'
    check(major > 0, 'The first 0.0.0 version has no earlier update fixture.')
    return f'{major - 1}.0.0'


def fixture_worker_source(original, archive):
    source = original.decode('utf-8')
    # Windows release archives preserve checkout CRLF; keep the fixture's newline style.
    source, count = re.subn(r'(?m)^    return env(\r?\n)',
                            lambda match: f'    env["EW_ARCHIVE"] = {str(archive)!r}  # CI fixture archive only'
                            + match.group(1) + match.group(0), source)
    check(count == 1, 'The fixture worker environment hook changed; review this check.')
    return source.encode('utf-8')


def print_update_diagnostics(install, data):
    """Bounded fixture logs explain native failures without exposing saved credentials."""
    secrets = []
    try:
        secrets.append((data / 'session-token').read_text(encoding='ascii').strip())
    except OSError:
        pass
    try:
        assistant = json.loads((data / 'assistant.json').read_text(encoding='utf-8-sig'))
        if isinstance(assistant, dict) and isinstance(assistant.get('key'), str):
            secrets.append(assistant['key'])
    except (OSError, ValueError):
        pass
    for path in (data / 'update-status.json', data / 'update.log', install / 'install.log', data / 'server.log'):
        try:
            text = path.read_bytes()[-8000:].decode('utf-8-sig', errors='replace')
        except OSError:
            continue
        for secret in secrets:
            if secret:
                text = text.replace(secret, '[redacted]')
        # Windows' stable Python may use cp1252 even when the log contains UTF-8.
        encoding = getattr(sys.stdout, 'encoding', None) or 'utf-8'
        output = f'CI update diagnostic: {path.name}\n{text}'
        print(output.encode(encoding, errors='backslashreplace').decode(encoding), flush=True)


def create_failed_release_fixture(install):
    failed = install / '.app-failed'
    check(not failed.exists(), 'The successful update left a failed release folder.')
    failed.mkdir()
    (failed / 'ci-uninstall-sentinel.txt').write_text('CI failed release must be removed by uninstall or purge.\n', encoding='utf-8')


def check_restarted_runtimes(base, token):
    for lesson, code, expected in (
        ('python-1', 'print("CI updated Python works")', 'CI updated Python works'),
        ('web-1', 'console.log("CI updated JavaScript works")', 'CI updated JavaScript works'),
    ):
        result = call(base, '/api/run', token, dict(lessonId=lesson, code=code, mode='run'))
        check(result.get('error') is None and result.get('stdout', '').strip() == expected,
              f'{lesson}: the restarted app could not execute its runtime.')


def stop_worker_tree(data):
    """Failure cleanup targets only the worker recorded by this isolated fixture."""
    try:
        status = json.loads((data / 'update-status.json').read_text(encoding='utf-8'))
        worker = status.get('pid')
        if status.get('status') not in ('updating', 'restarting') or type(worker) is not int or worker <= 0:
            return
        if os.name == 'nt':
            subprocess.run(['taskkill', '/PID', str(worker), '/T', '/F'], capture_output=True, timeout=20)
            return
        listed = subprocess.run(['ps', '-axo', 'pid=,ppid='], capture_output=True, text=True, check=True, timeout=10)
        parents = {int(pid): int(parent) for line in listed.stdout.splitlines() for pid, parent in [line.split()]}
        descendants = {worker}
        while True:
            expanded = descendants | {pid for pid, parent in parents.items() if parent in descendants}
            if expanded == descendants:
                break
            descendants = expanded
        for pid in descendants:
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
    except (OSError, ValueError, subprocess.SubprocessError):
        pass


def main(install, archive):
    install, archive = Path(install).resolve(), Path(archive).resolve()
    scratch = Path(os.environ.get('RUNNER_TEMP', '/nonexistent')).resolve()
    check(os.environ.get('CI') == 'true' and install.is_relative_to(scratch), 'This check only modifies CI installations under RUNNER_TEMP.')
    check(Path(os.environ.get('EW_HOME', '/nonexistent')).resolve() == install, 'EW_HOME must identify this disposable install.')
    check((install / '.engineering-workshop').is_file() and archive.is_file(), 'A marked install and candidate archive are required.')
    check(not Path(sys.executable).resolve().is_relative_to(install / 'app'), 'Run this check with stable runtime Python outside app/.venv.')
    check((archive.parent / 'SHA256SUMS').is_file(), 'Candidate checksums are required.')
    app, data = install / 'app', install / 'data'
    package = app / 'package.json'
    worker_file = app / 'scripts/update_worker.py'
    package_original, worker_original = package.read_bytes(), worker_file.read_bytes()
    metadata = json.loads(package_original)
    candidate, previous = metadata['version'], previous_version(metadata['version'])
    metadata['version'] = previous
    worker_fixture = fixture_worker_source(worker_original, archive)
    python = app / '.venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    env = {**os.environ, 'ML_WORKSHOP_PORT': str(port), 'ML_WORKSHOP_DATA_DIR': str(data)}
    base = f'http://127.0.0.1:{port}'
    succeeded = False
    try:
        atomic_bytes(package, (json.dumps(metadata, indent=2) + '\n').encode('utf-8'))
        atomic_bytes(worker_file, worker_fixture)
        started = subprocess.run([str(python), str(app / 'scripts/installed.py'), '--no-open'],
                                 env=env, capture_output=True, text=True, timeout=120)
        check(started.returncode == 0, 'The simulated older fixture server did not start.')
        token = (data / 'session-token').read_text(encoding='ascii').strip()
        old_pid = int((data / 'server.pid').read_text())
        check(call(base, '/api/health')['version'] == previous, 'The fixture did not serve the simulated older version.')
        profile = call(base, '/api/learning-path', token, dict(experience='new', goal='agents'))['profile']
        call(base, '/api/draft', token, dict(lessonId='python-1', code='# CI preserved draft', notes='CI preserved note', updatedAt=100))
        call(base, '/api/current', token, dict(lessonId='python-3'))
        result = call(base, '/api/run', token, dict(lessonId='foundations-1', code='def predict(x, weight, bias): return x * weight + bias', mode='check'))
        check(result['passed'], 'The fixture completion could not be created.')
        before = call(base, '/api/state', token)
        book = data / 'library/ci-update-book-sentinel.epub'
        book.parent.mkdir(exist_ok=True)
        book.write_bytes(b'CI book bytes must survive app replacement\n')
        book_original = book.read_bytes()
        assistant = data / 'assistant.json'
        if not assistant.exists():
            assistant.write_text('{"enabled": false, "key": "ci-synthetic"}', encoding='utf-8')
        assistant_original = assistant.read_bytes()
        status_file = data / 'update-status.json'
        status_file.write_text(json.dumps(dict(status='idle', latestVersion=candidate,
                                              checkedAt=datetime.now(timezone.utc).isoformat())), encoding='utf-8')
        status = call(base, '/api/update', token)
        check(status['supported'] and status['updateAvailable'], 'The real installed updater did not offer the candidate.')
        applied = call(base, '/api/update/apply', token, {})
        check(applied['status'] in ('updating', 'restarting', 'updated'), 'The real update action did not start.')
        deadline = time.monotonic() + 300
        while time.monotonic() < deadline:
            try:
                status = call(base, '/api/update', token)
                check(status['status'] != 'error', 'The updater reported an installation or restart failure.')
                if status['status'] == 'updated' and status['currentVersion'] == candidate:
                    break
            except (OSError, ValueError):
                pass  # A brief loopback disconnect is expected while replacing the server.
            time.sleep(.25)
        else:
            raise RuntimeError('The real detached update did not finish within five minutes.')
        check(call(base, '/api/health')['version'] == candidate, 'The restarted server has the wrong version.')
        check(call(base, '/api/session', token)['ok'], 'The original session could not reconnect.')
        check((data / 'session-token').read_text(encoding='ascii').strip() == token, 'The update changed the session token.')
        check(int((data / 'server.pid').read_text()) != old_pid, 'The updater did not replace the server process.')
        check(call(base, '/api/state', token) == before, 'The update changed drafts, notes, completion, activity or current lesson.')
        check(call(base, '/api/learning-path', token)['profile'] == profile, 'The update changed the saved learner profile.')
        check(book.read_bytes() == book_original, 'The update changed the library book sentinel.')
        check(assistant.read_bytes() == assistant_original, 'The update changed assistant settings.')
        check(worker_file.read_bytes() == worker_original, 'The new release retained fixture-only worker modifications.')
        check_restarted_runtimes(base, token)
        try:
            call(base, '/api/state')
            raise RuntimeError('The restarted server answered learner data without authentication.')
        except urllib.error.HTTPError as error:
            check(error.code == 403, 'The restarted server returned an unexpected authentication status.')
        backups = list((data / 'backups').glob('ml-workshop-*.json'))
        check(backups and any(json.loads(file.read_text(encoding='utf-8')).get('learnerProfile') == profile for file in backups),
              'The update did not back up the learner profile before installing.')
        deadline = time.monotonic() + 30
        while (install / '.install-lock').exists() and time.monotonic() < deadline:
            time.sleep(.1)
        check(not (install / '.install-lock').exists(), 'The completed update did not release its installer lock.')
        # The surrounding native CI workflow uninstalls/purges and must remove stale release code too.
        create_failed_release_fixture(install)
        succeeded = True
    except Exception:
        print_update_diagnostics(install, data)
        raise
    finally:
        if not succeeded:
            stop_worker_tree(data)
        stop = app / 'scripts/stop.py'
        if stop.is_file():
            stopped = subprocess.run([sys.executable, str(stop)], env=env, capture_output=True, text=True, timeout=60)
            check(stopped.returncode == 0, 'The update fixture server could not be stopped cleanly.')
        # If an early failure kept the old fixture, remove its deliberate version/archive modifications.
        if package.is_file() and json.loads(package.read_bytes()).get('version') == previous:
            atomic_bytes(package, package_original)
        if worker_file.is_file() and b'# CI fixture archive only' in worker_file.read_bytes():
            atomic_bytes(worker_file, worker_original)
    print('Real in-app update passed: detached worker survives server stop; same-port restart, authentication, profile, drafts, completions, books and assistant settings are preserved.')


if __name__ == '__main__':
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    main(sys.argv[1], sys.argv[2])
