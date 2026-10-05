#!/bin/zsh
set -e
cd "${0:A:h}"
if [[ ! -x .venv/bin/python ]]; then
  print 'Run Setup ML Workshop.command first, then open this installer again.'
  read '?Press Enter to close.'
  exit 1
fi
./script/build_and_run.sh
