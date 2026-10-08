"""Wait for a disposable test server and read its session token from the data folder, as the launcher does."""
from pathlib import Path
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from platform_paths import read_session_token


def server_token(url, data, process=None, attempts=80):
    for _ in range(attempts):
        try:
            with urllib.request.urlopen(url + '/api/health', timeout=1):
                pass
            token = read_session_token(data)
            if token:
                return token
        except OSError:
            if process is not None and process.poll() is not None:
                raise RuntimeError('Test server exited')
        time.sleep(.1)
    raise RuntimeError('Test server unavailable')
