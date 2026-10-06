"""Start once, wait for readiness, and open Engineering Workshop."""
import json
import os
import subprocess
import sys
import time
import urllib.request
import webbrowser

from platform_paths import ROOT, data_dir, detached_options, file_lock, installed, port, venv_python


def health(url):
    try:
        with urllib.request.urlopen(url + '/api/health', timeout=1) as response:
            return json.load(response)
    except (OSError, ValueError):
        return None


def main():
    data = data_dir()
    listen_port = port()
    url = f'http://127.0.0.1:{listen_port}'
    data.mkdir(parents=True, exist_ok=True)
    with file_lock(data / 'launch.lock'):
        status = health(url)
        if not status or status.get('app') != 'ml-workshop':
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
    if '--no-open' not in sys.argv:
        webbrowser.open(url)
    print(url)


if __name__ == '__main__':
    main()
