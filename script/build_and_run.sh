#!/bin/bash
set -euo pipefail
WORKSHOP_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$WORKSHOP_ROOT"
MODE="${1:-run}"
case "$MODE" in run|--verify|--logs) ;; *) echo "Usage: $0 [--verify|--logs]" >&2; exit 2 ;; esac
# Only the native shell is restarted; the learner server and data stay intact.
/usr/bin/pkill -x EngineeringWorkshop 2>/dev/null || true
.venv/bin/python scripts/install-launcher.py --open
if [[ "$MODE" == --verify ]]; then
  for attempt in {1..30}; do
    if /usr/bin/pgrep -x EngineeringWorkshop >/dev/null; then
      echo 'Engineering Workshop is running.'
      exit 0
    fi
    sleep 0.2
  done
  echo 'The native app did not launch.' >&2
  exit 1
elif [[ "$MODE" == --logs ]]; then
  /usr/bin/log stream --info --style compact --predicate 'process == "EngineeringWorkshop"'
fi
