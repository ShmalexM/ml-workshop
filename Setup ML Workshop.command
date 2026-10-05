#!/bin/zsh
set -e
cd "${0:A:h}"
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
if ! command -v uv >/dev/null || ! command -v npm >/dev/null; then
  print 'Setup requires uv and Node/npm. See README.md.'
  read '?Press Enter to close.'
  exit 1
fi
if [[ ! -x .venv/bin/python ]]; then
  uv venv --python 3.12 .venv
fi
uv pip sync --python .venv/bin/python requirements.lock
npm ci
npm run build
.venv/bin/python scripts/launch.py
