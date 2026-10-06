"""Open or stop a copy made by install.sh or install.ps1.

The installer keeps progress in <install folder>/data and Node.js in
<install folder>/runtime, next to the app folder that each update replaces.
Shortcuts run this file; pass --stop to stop the server, or --no-open to start
it without opening a browser.
"""
import os
from pathlib import Path
import sys

import launch
import stop

INSTALL = Path(__file__).resolve().parents[2]


def configure(environ, install=INSTALL):
    environ['ML_WORKSHOP_DATA_DIR'] = str(install / 'data')
    node = install / 'runtime' / 'node'
    if os.name != 'nt':
        node = node / 'bin'
    # The runner finds Node.js through PATH. An empty entry would mean the current folder.
    environ['PATH'] = os.pathsep.join(path for path in (str(node), environ.get('PATH')) if path)


def report(message):
    # Windows shortcuts start pythonw, which has no console to print to.
    if sys.stderr is None and os.name == 'nt':
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, message, 'Engineering Workshop', 0x10)
    elif sys.stderr is not None:
        print(message, file=sys.stderr)


def main(argv):
    configure(os.environ)
    try:
        if '--stop' in argv:
            stop.main()
        else:
            launch.main()
    except (OSError, RuntimeError, ValueError) as exc:
        report(str(exc))
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
