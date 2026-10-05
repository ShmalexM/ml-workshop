"""Paths and process options shared by the platform entrypoints."""
from contextlib import contextmanager
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def venv_python(root=ROOT):
    return root / '.venv' / ('Scripts/python.exe' if sys.platform == 'win32' else 'bin/python')


def data_dir(root=ROOT):
    path = Path(os.environ.get('ML_WORKSHOP_DATA_DIR', root / 'data'))
    # Relative overrides have the same meaning in the launcher and server.
    return (root / path).resolve()


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
