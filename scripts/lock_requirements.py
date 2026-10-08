"""Regenerate requirements.lock and requirements-light.lock with uv.

Both files pin every package with its SHA-256 hashes for macOS, Linux and Windows on
Python 3.12, and scripts/setup.py installs them with --require-hashes.
requirements.lock covers requirements.txt. requirements-light.lock covers the light
install: requirements.txt without the ML packages. PyTorch comes from its CPU index.

    python scripts/lock_requirements.py            # keep the current pins where possible
    python scripts/lock_requirements.py --upgrade  # newest versions allowed by requirements.txt

Needs uv on PATH. Run it after every change to requirements.txt.
"""
import argparse
import shutil
import subprocess

import setup


def compile_lock(uv, source, output, upgrade, text=None):
    command = [uv, 'pip', 'compile', source, '--output-file', output, '--universal', '--python-version', '3.12',
               '--generate-hashes', '--torch-backend', 'cpu', '--no-config', '--quiet',
               '--custom-compile-command', 'python scripts/lock_requirements.py']
    if upgrade:
        command.append('--upgrade')
    subprocess.run(command, cwd=setup.ROOT, input=text, text=True, check=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--upgrade', action='store_true', help='Move every package to the newest version allowed by requirements.txt.')
    args = parser.parse_args(argv)
    uv = shutil.which('uv')
    if not uv:
        raise SystemExit('Install uv (https://docs.astral.sh/uv/), then run this again.')
    compile_lock(uv, 'requirements.txt', setup.requirements_file(ml=True).name, args.upgrade)
    light = ''.join(line + '\n' for line in setup.light_requirements())
    compile_lock(uv, '-', setup.requirements_file(ml=False).name, args.upgrade, light)


if __name__ == '__main__':
    main()
