"""Package a built checkout for the one-line installers.

Run `npm run build` first. Writes engineering-workshop.tar.gz (macOS and Linux),
engineering-workshop.zip (Windows) and SHA256SUMS into release/. Both archives hold
one top-level engineering-workshop/ folder with the tracked source files and dist/.
"""
import gzip
import hashlib
import io
import os
from pathlib import Path, PurePosixPath
import subprocess
import tarfile
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
NAME = 'engineering-workshop'
# Learner data, local environments, build tools, private notes and agent settings.
EXCLUDED_TOP = {'.git', '.claude', '.codex', '.local', '.venv', 'data', 'node_modules', 'release', 'PLAN.md'}


def included(path):
    parts = PurePosixPath(path).parts
    return (parts[0] not in EXCLUDED_TOP
            and not (parts[0] == 'docs' and parts[-1].startswith('claude-'))
            and '__pycache__' not in parts and not path.endswith('.pyc'))


def git(root, *args):
    return subprocess.run(['git', *args], cwd=root, capture_output=True, check=True).stdout


def release_files(root=ROOT):
    """Return {archive path: file mode} for tracked and new unignored files plus dist/."""
    if not (root / 'dist/index.html').is_file():
        raise SystemExit('dist/index.html is missing. Run `npm run build` first.')
    modes = {}
    for line in git(root, 'ls-files', '--stage', '-z').decode().split('\0'):
        if line:
            info, path = line.split('\t', 1)
            modes[path] = 0o755 if info.startswith('100755') else 0o644
    untracked = git(root, 'ls-files', '--others', '--exclude-standard', '-z').decode().split('\0')
    built = [path.relative_to(root).as_posix() for path in (root / 'dist').rglob('*')]
    files = {}
    for path in [*modes, *untracked, *built]:
        if path and included(path) and (root / path).is_file() and not (root / path).is_symlink():
            mode = modes.get(path)
            if mode is None:
                mode = 0o755 if os.name != 'nt' and os.access(root / path, os.X_OK) else 0o644
            files[path] = mode
    return dict(sorted(files.items()))


def source_date(root):
    # The last commit time keeps archives reproducible for the same checkout.
    return int(os.environ.get('SOURCE_DATE_EPOCH') or git(root, 'log', '-1', '--format=%ct').strip())


def write_tar(root, files, target, mtime):
    with open(target, 'wb') as raw, gzip.GzipFile(fileobj=raw, mode='wb', mtime=mtime) as compressed, \
            tarfile.open(fileobj=compressed, mode='w', format=tarfile.PAX_FORMAT) as archive:
        for path, mode in files.items():
            data = (root / path).read_bytes()
            info = tarfile.TarInfo(f'{NAME}/{path}')
            info.size, info.mode, info.mtime = len(data), mode, mtime
            archive.addfile(info, io.BytesIO(data))


def write_zip(root, files, target, mtime):
    stamp = max(mtime, 315532800)  # ZIP dates start in 1980.
    date_time = time.gmtime(stamp)[:6]
    with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path, mode in files.items():
            info = zipfile.ZipInfo(f'{NAME}/{path}', date_time)
            info.external_attr = (0o100000 | mode) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, (root / path).read_bytes())


def package(root=ROOT, out=None):
    out = Path(out or root / 'release')
    out.mkdir(parents=True, exist_ok=True)
    files = release_files(root)
    mtime = source_date(root)
    targets = [out / f'{NAME}.tar.gz', out / f'{NAME}.zip']
    write_tar(root, files, targets[0], mtime)
    write_zip(root, files, targets[1], mtime)
    sums = ''.join(f'{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}\n' for path in targets)
    (out / 'SHA256SUMS').write_text(sums, newline='\n')
    return targets + [out / 'SHA256SUMS']


if __name__ == '__main__':
    for path in package():
        print(f'{path}  {path.stat().st_size:,} bytes')
