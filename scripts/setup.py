"""Install Engineering Workshop for macOS, Linux, or Windows."""
import argparse
import re
import shutil
import subprocess
import sys

from platform_paths import ROOT, venv_python

ML_PACKAGES = {'torch', 'tensorflow', 'transformers', 'tokenizers',
               'langchain-core', 'llama-index-core', 'numba'}
# The lock files take PyTorch from its CPU index: the lessons never use a GPU, and the
# CUDA builds on PyPI add several GB on Linux.
TORCH_CPU_INDEX = 'https://download.pytorch.org/whl/cpu'


def requirements_file(ml=True):
    # Both files pin every package with its SHA-256 hashes for macOS, Linux and Windows.
    # scripts/lock_requirements.py makes them from requirements.txt.
    return ROOT / ('requirements.lock' if ml else 'requirements-light.lock')


def install_options(ml, uv):
    """Options for a hash-checked `uv pip install` or `pip install` of a lock file."""
    options = ['--require-hashes', '-r', str(requirements_file(ml))]
    if ml:
        options += ['--torch-backend', 'cpu'] if uv else ['--extra-index-url', TORCH_CPU_INDEX]
    return options


def light_requirements():
    """The lines of requirements.txt for the light install, without the ML packages."""
    return [line.strip() for line in (ROOT / 'requirements.txt').read_text().splitlines()
            if line.strip() and not line.lstrip().startswith('#')
            and re.split(r'[<>=!~;\[]', line.strip(), maxsplit=1)[0].lower() not in ML_PACKAGES]


def check_prerequisites(need_node=True):
    if sys.version_info < (3, 12):
        raise RuntimeError('Engineering Workshop needs Python 3.12 or newer. Install it and rerun setup.')
    if not need_node:
        return None
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
    parser.add_argument('--no-build', action='store_true', help='Use the prebuilt dist/ folder from a release archive; skip the Node.js check and the interface build.')
    args = parser.parse_args(argv)
    npm = check_prerequisites(need_node=not args.no_build)
    if args.no_build and not (ROOT / 'dist/index.html').exists():
        raise RuntimeError('dist/index.html is missing. Run setup without --no-build to build the interface.')
    uv = shutil.which('uv')
    python = venv_python()
    if not python.exists():
        if uv:
            run([uv, 'venv', '--python', sys.executable, ROOT / '.venv'])
        else:
            run([sys.executable, '-m', 'venv', ROOT / '.venv'])
    run([python, '-c', 'import sys; sys.exit(0 if sys.version_info >= (3, 12) else "The existing .venv needs Python 3.12 or newer.")'])
    options = install_options(ml=not args.no_ml, uv=bool(uv))
    if uv:
        run([uv, 'pip', 'install', '--python', python, *options])
    else:
        # An existing uv-created environment may not contain pip.
        run([python, '-m', 'ensurepip', '--upgrade'])
        run([python, '-m', 'pip', 'install', *options])
    if not args.no_build:
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
