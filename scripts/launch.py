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
    start(data, listen_port, url)
    url = session_url(url, data)
    if '--no-open' not in sys.argv:
        webbrowser.open(url)
    print(url)


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
        else:
            python = venv_python()
            if not python.exists() or not (ROOT / 'dist/index.html').exists():
                if installed():
                    raise RuntimeError('Engineering Workshop is missing files. Run the install command again; your progress is kept.')
                raise RuntimeError(f'Engineering Workshop needs setup. Run the setup wrapper for your OS in {ROOT}; see README.md.')
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
