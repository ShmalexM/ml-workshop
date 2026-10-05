"""Install Engineering Workshop for macOS, Linux, or Windows."""
import argparse
import platform
import re
import shutil
import subprocess
import sys

from platform_paths import ROOT, venv_python

ML_PACKAGES = {'torch', 'tensorflow', 'transformers', 'tokenizers',
               'langchain-core', 'llama-index-core', 'numba'}


def requirements_file():
    # requirements.lock is a macOS arm64 snapshot, not a portable lockfile.
    name = 'requirements.lock' if sys.platform == 'darwin' and platform.machine() == 'arm64' else 'requirements.txt'
    return ROOT / name


def light_requirements():
    return [line.strip() for line in (ROOT / 'requirements.txt').read_text().splitlines()
            if line.strip() and not line.lstrip().startswith('#')
            and re.split(r'[<>=!~;\[]', line.strip(), maxsplit=1)[0].lower() not in ML_PACKAGES]


def check_prerequisites():
    if sys.version_info < (3, 12):
        raise RuntimeError('Engineering Workshop needs Python 3.12 or newer. Install it and rerun setup.')
    node = shutil.which('node')
    npm = shutil.which('npm.cmd' if sys.platform == 'win32' else 'npm')
    if not node or not npm:
        raise RuntimeError('Install Node.js 22.13 or newer (including npm), reopen your terminal, and rerun setup.')
    version = subprocess.check_output([node, '--version'], text=True).strip()
    match = re.fullmatch(r'v?(\d+)\.(\d+)\.(\d+)(?:-.*)?', version)
    if not match or tuple(map(int, match.groups())) < (22, 13, 0):
        raise RuntimeError(f'Node.js 22.13 or newer is required; found {version}.')
    return npm


def run(args):
    subprocess.run([str(arg) for arg in args], cwd=ROOT, check=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--no-ml', action='store_true', help='Skip ML packages; keep Python/JavaScript engineering lessons and book imports.')
    parser.add_argument('--no-launch', action='store_true', help='Install and build without starting the server or opening a browser.')
    args = parser.parse_args(argv)
    npm = check_prerequisites()
    uv = shutil.which('uv')
    python = venv_python()
    if not python.exists():
        if uv:
            run([uv, 'venv', '--python', sys.executable, ROOT / '.venv'])
        else:
            run([sys.executable, '-m', 'venv', ROOT / '.venv'])
    run([python, '-c', 'import sys; sys.exit(0 if sys.version_info >= (3, 12) else "The existing .venv needs Python 3.12 or newer.")'])
    packages = light_requirements() if args.no_ml else ['-r', str(requirements_file())]
    if uv:
        run([uv, 'pip', 'install', '--python', python, *packages])
    else:
        # An existing uv-created environment may not contain pip.
        run([python, '-m', 'ensurepip', '--upgrade'])
        run([python, '-m', 'pip', 'install', *packages])
    run([npm, 'ci'])
    run([npm, 'run', 'build'])
    if args.no_ml:
        print('Light install complete. ML lessons need another setup run without --no-ml. Existing ML packages are kept.', flush=True)
    if not args.no_launch:
        run([python, ROOT / 'scripts/launch.py'])


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, OSError, subprocess.CalledProcessError) as exc:
        raise SystemExit(f'Setup failed: {exc}')
