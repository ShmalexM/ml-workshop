"""Paths and process options shared by the platform entrypoints."""
from contextlib import contextmanager
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
# install.sh and install.ps1 write this file into the install folder, next to app/ and data/.
INSTALL_MARKER = '.engineering-workshop'
# The server keeps its browser session token here. Launchers read it and open #session=<token>.
SESSION_TOKEN = 'session-token'
TOKEN_PATTERN = re.compile(r'[A-Za-z0-9_-]{32,128}')


def venv_python(root=ROOT):
    return root / '.venv' / ('Scripts/python.exe' if sys.platform == 'win32' else 'bin/python')


def installed(root=ROOT):
    """True for a copy made by the one-line installer: <install folder>/app with the marker next to it."""
    return root.name == 'app' and (root.parent / INSTALL_MARKER).is_file()


def data_dir(root=ROOT):
    # Updates replace app/, so an installed copy keeps progress in the data/ folder next to it.
    default = root.parent / 'data' if installed(root) else root / 'data'
    path = Path(os.environ.get('ML_WORKSHOP_DATA_DIR', default))
    # Relative overrides have the same meaning in the launcher and server.
    return (root / path).resolve()


def read_session_token(data):
    """The saved session token in the data folder, or None if it is missing or damaged."""
    try:
        token = (Path(data) / SESSION_TOKEN).read_text(encoding='ascii').strip()
    except (OSError, UnicodeError):
        return None
    return token if TOKEN_PATTERN.fullmatch(token) else None


def session_token(data):
    """Return the saved session token. Create a new one only when the file is missing or damaged."""
    path = Path(data) / SESSION_TOKEN
    token = read_session_token(data)
    if token:
        if os.name != 'nt':
            path.chmod(0o600)
        return token
    token = secrets.token_urlsafe(32)
    # Write a private file, then rename it, so a reader never sees a partial token.
    temporary = path.with_name(f'.{SESSION_TOKEN}-{os.getpid()}')
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, 'w', encoding='ascii') as stream:
        stream.write(token + '\n')
    os.replace(temporary, path)
    return token


def port():
    value = int(os.environ.get('ML_WORKSHOP_PORT', '7318'))
    if not 1 <= value <= 65535:
        raise ValueError('ML_WORKSHOP_PORT must be between 1 and 65535.')
    return value


def detached_options():
    if os.name == 'nt':
        return dict(creationflags=(subprocess.DETACHED_PROCESS |
                                   subprocess.CREATE_NEW_PROCESS_GROUP |
                                   subprocess.CREATE_NO_WINDOW))
    return dict(start_new_session=True)


@contextmanager
def file_lock(path):
    # Do not truncate: Windows locks a byte at the current file position.
    with path.open('a+b') as lock:
        if os.name == 'nt':
            import msvcrt
            lock.seek(0, os.SEEK_END)
            if lock.tell() == 0:
                lock.write(b'\0')
                lock.flush()
            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_LOCK, 1)
            try:
                yield
            finally:
                lock.seek(0)
                msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(lock, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)
