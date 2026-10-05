"""Build and install a local native Mac window; learner data stays in the checkout."""
from pathlib import Path
import argparse
import datetime
import platform
import plistlib
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
NAME = 'Engineering Workshop'
IDENTIFIER = 'dev.ml-workshop.desktop'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--open', action='store_true', help='Open the installed Mac app')
    args = parser.parse_args()
    if sys.platform != 'darwin':
        raise SystemExit('The Mac app installer requires macOS. Use scripts/launch.py for browser access.')
    destination = Path.home() / 'Applications' / (NAME + '.app')
    if destination.exists():
        with (destination / 'Contents/Info.plist').open('rb') as f:
            if plistlib.load(f).get('CFBundleIdentifier') != IDENTIFIER:
                raise SystemExit(f'Refusing to replace an unrelated app at {destination}')
    build = ROOT / '.local/native-build'
    build.mkdir(parents=True, exist_ok=True)
    bundle = build / (NAME + '.app')
    contents = bundle / 'Contents'
    for folder in ('MacOS', 'Resources'):
        (contents / folder).mkdir(parents=True, exist_ok=True)
    subprocess.run(['/usr/bin/xcrun', 'swiftc', '-O', '-target', platform.machine() + '-apple-macos13.0', '-swift-version', '5', '-framework', 'AppKit', '-framework', 'WebKit', '-o', str(contents / 'MacOS/EngineeringWorkshop'), str(ROOT / 'native/WorkshopApp.swift')], check=True)
    shutil.copyfile(ROOT / 'assets/Workshop.icns', contents / 'Resources/Workshop.icns')
    info = dict(CFBundleName=NAME, CFBundleDisplayName=NAME, CFBundleIdentifier=IDENTIFIER,
                CFBundlePackageType='APPL', CFBundleExecutable='EngineeringWorkshop', CFBundleIconFile='Workshop',
                CFBundleShortVersionString='1.0', CFBundleVersion='1', LSMinimumSystemVersion='13.0',
                NSPrincipalClass='NSApplication', NSHighResolutionCapable=True,
                NSAppTransportSecurity={'NSAllowsLocalNetworking': True}, WorkshopRoot=str(ROOT))
    with (contents / 'Info.plist').open('wb') as f:
        plistlib.dump(info, f)
    subprocess.run(['/usr/bin/codesign', '--force', '--sign', '-', str(bundle)], check=True)
    subprocess.run(['/usr/bin/codesign', '--verify', '--strict', str(bundle)], check=True)
    destination.parent.mkdir(exist_ok=True)
    staging = destination.with_name('.Engineering Workshop.installing.app')
    if staging.exists():
        raise SystemExit(f'Previous staging bundle exists: {staging}. Inspect before retrying.')
    shutil.copytree(bundle, staging)
    if destination.exists():
        # Preserve the previous app bundle; never touch learner data or books.
        stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        backup = ROOT / '.local/launcher-backups' / stamp
        backup.mkdir(parents=True)
        destination.rename(backup / destination.name)
    staging.rename(destination)
    link = Path.home() / 'Desktop' / (NAME + '.app')
    if not link.exists() and not link.is_symlink():
        link.symlink_to(destination)
    print(destination)
    if args.open:
        subprocess.run(['/usr/bin/open', str(destination)], check=True)


if __name__ == '__main__':
    main()
