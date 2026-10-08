"""Start once, wait for readiness, and open Engineering Workshop."""
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser

from platform_paths import ROOT, data_dir, detached_options, file_lock, installed, port, read_session_token, venv_python
from stop import is_our_server, stop_server

VERSION = json.loads((ROOT / 'package.json').read_text(encoding='utf-8'))['version']


def health(url):
    try:
        with urllib.request.urlopen(url + '/api/health', timeout=1) as response:
            return json.load(response)
    except (OSError, ValueError):
        return None


def token_accepted(url, token):
    """False when the running server rejects this data folder's session token."""
    request = urllib.request.Request(url + '/api/session', headers={'X-Workshop-Token': token})
    try:
        with urllib.request.urlopen(request, timeout=2):
            return True
    except urllib.error.HTTPError as error:
        return error.code != 403
    except OSError:
        return True


def session_url(url, data):
    """The address that connects a browser: the server's token goes in the fragment, which is never sent over HTTP."""
    token = read_session_token(data)
    return f'{url}/#session={token}' if token else url


def main():
    data = data_dir()
    listen_port = port()
    url = f'http://127.0.0.1:{listen_port}'
    # The data folder, server.log and the server process are private to this user.
    # The browser is started later with the original umask.
    previous_umask = os.umask(0o077)
    try:
        start(data, listen_port, url)
    finally:
        os.umask(previous_umask)
    url = session_url(url, data)
    if '--no-open' not in sys.argv:
        webbrowser.open(url)
    print(url)


def runnable_python():
    python = venv_python()
    if not python.exists() or not (ROOT / 'dist/index.html').exists():
        if installed():
            raise RuntimeError('Engineering Workshop is missing files. Run the install command again; your progress is kept.')
        raise RuntimeError(f'Engineering Workshop needs setup. Run the setup wrapper for your OS in {ROOT}; see README.md.')
    return python


def stop_other_version(data, status):
    """Stop a server from another version that uses this data folder, so this version can start.

    An update replaces the app's files but leaves the old server running. It would serve the new
    interface with the old API. Progress is saved as it is made, so a restart loses nothing; it waits
    only for an exercise that is running.
    """
    running = f"version {status['version']}" if status.get('version') else 'an older version'
    if status.get('busy'):
        raise RuntimeError(f'The running Engineering Workshop is {running} and is running an exercise. This copy is version {VERSION}. '
                           'Wait for the exercise to finish, then open Engineering Workshop again to restart it.')
    pid_file = data / 'server.pid'
    try:
        pid = int(pid_file.read_text())
    except (OSError, ValueError):
        pid = None
    if pid is None or not is_our_server(pid):
        raise RuntimeError(f'The running Engineering Workshop is {running}, and this copy is version {VERSION}. '
                           'Stop it with the Stop command for your system, then open Engineering Workshop again.')
    stop_server(pid)
    pid_file.unlink(missing_ok=True)
    print(f'Restarted Engineering Workshop: {running} was running, and this copy is version {VERSION}.', file=sys.stderr)


def start(data, listen_port, url):
    data.mkdir(parents=True, exist_ok=True)
    with file_lock(data / 'launch.lock'):
        status = health(url)
        if status and status.get('app') == 'ml-workshop':
            # A browser can connect only to a server that uses this data folder's token.
            token = read_session_token(data)
            if not token:
                raise RuntimeError('Engineering Workshop is running, but its session-token file is missing. Stop Engineering Workshop, then open it again.')
            if not token_accepted(url, token):
                raise RuntimeError(f'Port {listen_port} is used by another copy of Engineering Workshop, which keeps its progress in a different folder. Stop that copy, then open this one again.')
            if status.get('version') == VERSION:
                return
            # Check this copy before stopping the running one.
            python = runnable_python()
            stop_other_version(data, status)
        else:
            python = runnable_python()
        with (data / 'server.log').open('ab') as log:
            process = subprocess.Popen(
                [str(python), str(ROOT / 'backend/server.py'), '--port', str(listen_port)],
                cwd=ROOT, env={**os.environ, 'ML_WORKSHOP_DATA_DIR': str(data)},
                stdout=log, stderr=log, stdin=subprocess.DEVNULL, **detached_options())
        (data / 'server.pid').write_text(str(process.pid))
        for _ in range(80):
            if process.poll() is not None:
                raise RuntimeError(f'Engineering Workshop could not start. Port {listen_port} may be in use. See {data}/server.log.')
            status = health(url)
            if status and status.get('app') == 'ml-workshop':
                break
            time.sleep(.15)
        else:
            raise RuntimeError(f'Engineering Workshop did not become ready. See {data}/server.log.')


if __name__ == '__main__':
    main()
