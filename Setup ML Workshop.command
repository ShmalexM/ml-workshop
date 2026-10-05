#!/bin/zsh
set -e
cd "${0:A:h}"
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
if command -v uv >/dev/null; then
  exec uv run --no-project --python 3.12 scripts/setup.py "$@"
fi
exec python3 scripts/setup.py "$@"
