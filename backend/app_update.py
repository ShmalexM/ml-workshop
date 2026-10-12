"""Token-protected update controls for marked, installer-owned copies only."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import threading
import urllib.request

from platform_paths import file_lock, installed
from update_worker import ACTIVE, installer_environment, process_alive, read_status, timestamp, valid_version, write_status

LATEST_API = 'https://api.github.com/repos/ShmalexM/ml-workshop/releases/latest'
RELEASES = 'https://github.com/ShmalexM/ml-workshop/releases'


class UpdateConflict(ValueError):
    pass


def exact_empty(body):
    if type(body) is not dict or body:
        raise ValueError('This update action accepts an empty object only.')


def newer(latest, current):
    return valid_version(latest) and valid_version(current) and tuple(map(int, latest.split('.'))) > tuple(map(int, current.split('.')))


class Updater:
    def __init__(self, root, data, version):
        self.root, self.data, self.version = Path(root).resolve(), Path(data).resolve(), version
        self.lock = threading.Lock()
        self.base_python = Path(getattr(sys, '_base_executable', sys.executable)).resolve()

    def supported(self):
        return (installed(self.root) and self.data == self.root.parent / 'data'
                and self.base_python.is_file() and not self.base_python.is_relative_to(self.root)
                and (sys.platform == 'win32' or sys.platform == 'darwin' or sys.platform.startswith('linux')))

    def raw_status(self):
        raw = read_status(self.data)
        if (raw.get('status') in ACTIVE and not process_alive(raw.get('pid'))) or raw.get('status') == 'checking':
            try:
                age = (datetime.now(timezone.utc) - datetime.fromisoformat(raw['startedAt'])).total_seconds()
            except (KeyError, ValueError, TypeError):
                age = 60
            # The launch reservation has no PID for the few milliseconds before bootstrap starts.
            if age > 30:
                write_status(self.data, status='error', error='The update was interrupted. Your saved work is kept. Try again.',
                             phase='The update was interrupted. Your saved work is kept. Try again.')
                raw = read_status(self.data)
        return raw

    def busy(self):
        return self.raw_status().get('status') in ACTIVE

    def status(self):
        raw = self.raw_status()
        latest = raw.get('latestVersion') if valid_version(raw.get('latestVersion')) else None
        status = raw.get('status')
        if status not in {'idle', 'checking', 'updating', 'restarting', 'updated', 'error'}:
            status = 'idle'
        supported = self.supported()
        message = raw.get('phase') if isinstance(raw.get('phase'), str) else 'Check for the latest stable release.'
        if not supported and status not in {'checking', 'error'}:
            message = 'This is a source checkout or custom installation. Export progress, stop the app, then update the checkout and run setup again.'
        return dict(installed=installed(self.root), supported=supported, currentVersion=self.version, latestVersion=latest,
                    updateAvailable=bool(newer(latest, self.version)), status=status, message=message,
                    error=raw.get('error') if isinstance(raw.get('error'), str) else None,
                    releaseUrl=RELEASES + ('/tag/v' + latest if latest else '/latest'),
                    checkedAt=raw.get('checkedAt') if isinstance(raw.get('checkedAt'), str) else None)

    def check(self, body):
        exact_empty(body)
        if not self.lock.acquire(blocking=False):
            raise UpdateConflict('An update action is already running.')
        try:
            with file_lock(self.data / 'update-launch.lock'):
                if self.busy():
                    raise UpdateConflict('An update is already running.')
                write_status(self.data, status='checking', phase='Checking the latest stable release.', startedAt=timestamp(), error=None)
                try:
                    request = urllib.request.Request(LATEST_API, headers={'Accept': 'application/vnd.github+json', 'User-Agent': 'Engineering-Workshop-Updater'})
                    with urllib.request.urlopen(request, timeout=10) as response:
                        payload = response.read(256001)
                    if len(payload) > 256000:
                        raise ValueError('release metadata size')
                    release = json.loads(payload)
                    tag = release.get('tag_name')
                    latest = tag[1:] if isinstance(tag, str) and tag.startswith('v') else None
                    if not valid_version(latest) or release.get('draft') is not False or release.get('prerelease') is not False:
                        raise ValueError('stable release required')
                    message = 'A new release is available.' if newer(latest, self.version) else 'You have the latest stable version.'
                    write_status(self.data, status='idle', latestVersion=latest, checkedAt=timestamp(), phase=message, error=None)
                except (OSError, ValueError, TypeError, AttributeError, RecursionError):
                    message = 'Could not check for updates. Check your internet connection and try again.'
                    write_status(self.data, status='error', phase=message, error=message)
            return self.status()
        finally:
            self.lock.release()

    def apply(self, body, port, backup):
        exact_empty(body)
        if not self.supported():
            raise UpdateConflict('In-app updates require a standard installer copy. Follow the update instructions for this checkout.')
        if not self.lock.acquire(blocking=False):
            raise UpdateConflict('An update action is already running.')
        try:
            with file_lock(self.data / 'update-launch.lock'):
                if self.busy():
                    raise UpdateConflict('An update is already running.')
                raw = self.raw_status()
                latest = raw.get('latestVersion')
                if not newer(latest, self.version):
                    raise UpdateConflict('Check for a newer stable release before updating.')
                backup()
                work = self.data / 'update-work'
                work.mkdir(mode=0o700, exist_ok=True)
                worker = work / 'update_worker.py'
                shutil.copyfile(self.root / 'scripts/update_worker.py', worker)
                extension = 'ps1' if os.name == 'nt' else 'sh'
                shutil.copyfile(self.root / ('install.' + extension), work / ('install.' + extension))
                write_status(self.data, status='updating', phase='Preparing the update. Your saved work has been backed up.',
                             startedAt=timestamp(), pid=None, error=None)
                # Light installs remain light. A full install keeps the ML package setup path.
                light = not ((self.root / '.venv/Lib/site-packages/torch').is_dir()
                             or any((self.root / '.venv/lib').glob('python*/site-packages/torch')))
                command = [str(self.base_python), str(worker), '--bootstrap', '--install', str(self.root.parent),
                           '--data', str(self.data), '--port', str(port), '--target', latest, '--previous', self.version]
                if light:
                    command.append('--light')
                try:
                    result = subprocess.run(command, cwd=self.root.parent, stdin=subprocess.DEVNULL,
                                            env=installer_environment(self.root.parent,self.data,port,latest,light),
                                            capture_output=True, text=True, timeout=10)
                    if result.returncode or not result.stdout.strip().isdigit():
                        raise RuntimeError('worker start')
                    write_status(self.data, pid=int(result.stdout.strip()))
                except (OSError, subprocess.SubprocessError, RuntimeError):
                    message = 'The updater could not start. Your current app and saved work are unchanged. Try again.'
                    write_status(self.data, status='error', phase=message, error=message)
            return self.status()
        finally:
            self.lock.release()
