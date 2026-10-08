#!/bin/sh
# Install, update or remove Engineering Workshop on macOS or Linux.
#
#   Install or update:
#     curl -fsSL https://raw.githubusercontent.com/ShmalexM/ml-workshop/main/install.sh | sh
#   Remove the app and keep your progress:
#     curl -fsSL https://raw.githubusercontent.com/ShmalexM/ml-workshop/main/install.sh | sh -s -- --uninstall
#   Remove everything, including your progress: add --purge after --uninstall.
#
# Everything goes into one folder, ~/.local/share/engineering-workshop. No admin rights are
# needed, and shell profiles and system settings are not changed.
#   app/      the app; each update replaces it
#   data/     your progress; updates and --uninstall keep it
#   runtime/  uv, Python 3.12, Node.js (when needed) and the download cache
#
# Settings for testing: EW_HOME (install folder), EW_ARCHIVE (local release archive; a
# SHA256SUMS file next to it is checked), EW_LIGHT=1 (skip the ML libraries),
# EW_NO_LAUNCH=1 (do not start the app), EW_NO_SHORTCUTS=1 (no app or menu entry).

set -eu

RELEASE_URL=https://github.com/ShmalexM/ml-workshop/releases/latest/download
UV_VERSION=0.12.23 # Keep in step with install.ps1.
NODE_MAJOR=24      # Same major version as .nvmrc.
# The native Mac app from scripts/install-launcher.py uses dev.ml-workshop.desktop.
APP_ID=dev.ml-workshop.launcher
ML_NOTE='The PyTorch, TensorFlow, Modern AI stack and CUDA lessons need them; all other lessons work.'

say() { printf '%s\n' "$*"; }

log() { printf '%s\n' "$*" >>"$LOG"; }

fail() {
  FAILED=1
  say "$1" >&2
  if [ -n "$LOG" ] && [ -s "$LOG" ]; then say "Details: $LOG" >&2; fi
  exit 1
}

# Explain exits that did not come from fail(), such as Ctrl-C or an unexpected error.
on_exit() {
  status=$?
  if [ "$status" != 0 ] && [ "$FAILED" = 0 ]; then
    say "Stopped before finishing." >&2
    if [ -n "$LOG" ] && [ -s "$LOG" ]; then say "Details: $LOG" >&2; fi
  fi
}

have() { command -v "$1" >/dev/null 2>&1; }

# Run a command with its output in the log.
run() {
  log "+ $*"
  "$@" </dev/null >>"$LOG" 2>&1
}

download() {
  log "+ download $1"
  if have curl; then
    curl --proto '=https' --tlsv1.2 -fsSL --retry 3 --connect-timeout 30 -o "$2" "$1" </dev/null >>"$LOG" 2>&1
  else
    wget -q -O "$2" "$1" </dev/null >>"$LOG" 2>&1
  fi
}

sha256_of() {
  if have sha256sum; then sha256sum <"$1"; else shasum -a 256 <"$1"; fi | cut -d ' ' -f 1
}

# Check file $1 against the checksum listed for name $2 in checksum file $3.
verify() {
  expected=$(awk -v name="$2" '$2 == name || $2 == "*" name { print $1; exit }' "$3")
  actual=$(sha256_of "$1")
  log "sha256 $2: expected $expected, got $actual"
  [ -n "$expected" ] && [ "$expected" = "$actual" ]
}

# Quote $1 for a POSIX shell script.
shell_quote() { printf "'%s'" "$(printf '%s' "$1" | sed "s/'/'\\\\''/g")"; }

# Quote $1 as one argument of a .desktop Exec line.
desktop_quote() {
  printf '"%s"' "$(printf '%s' "$1" | sed -e 's/[\\"`$]/\\&/g' -e 's/\\/\\\\/g' -e 's/%/%%/g')"
}

detect_platform() {
  case $(uname -s) in
    Darwin) OS=macos ;;
    Linux) OS=linux ;;
    *) fail "This installer is for macOS and Linux. On Windows, use the PowerShell command from the README." ;;
  esac
  ARCH=$(uname -m)
  # Terminal can run under Rosetta on Apple silicon, which reports x86_64.
  if [ "$OS" = macos ] && [ "$(sysctl -n sysctl.proc_translated 2>/dev/null || true)" = 1 ]; then
    ARCH=arm64
  fi
  case $ARCH in
    arm64 | aarch64) ARCH=arm64 ;;
    x86_64 | amd64) ARCH=x64 ;;
    *) fail "This computer's processor type ($ARCH) is not supported." ;;
  esac
  case $OS-$ARCH in
    macos-arm64) UV_TARGET=aarch64-apple-darwin NODE_TARGET=darwin-arm64 ;;
    macos-x64) UV_TARGET=x86_64-apple-darwin NODE_TARGET=darwin-x64 ;;
    # The static musl build of uv runs on every Linux distribution.
    linux-arm64) UV_TARGET=aarch64-unknown-linux-musl NODE_TARGET=linux-arm64 ;;
    linux-x64) UV_TARGET=x86_64-unknown-linux-musl NODE_TARGET=linux-x64 ;;
  esac
}

set_paths() {
  EW_HOME=${EW_HOME:-$HOME/.local/share/engineering-workshop}
  case $EW_HOME in /*) ;; *) EW_HOME=$(pwd)/$EW_HOME ;; esac
  APP=$EW_HOME/app DATA=$EW_HOME/data RUNTIME=$EW_HOME/runtime
  MARKER=$EW_HOME/.engineering-workshop
  STAGE=$EW_HOME/.app-new OLD=$EW_HOME/.app-old WORK=$EW_HOME/.download
  if [ "$OS" = macos ]; then
    SHORTCUT="$HOME/Applications/Engineering Workshop.app"
  else
    SHORTCUT=${XDG_DATA_HOME:-$HOME/.local/share}/applications/engineering-workshop.desktop
  fi
}

check_tools() {
  if [ "$(id -u)" = 0 ] && [ -n "${SUDO_USER:-}" ]; then
    fail "Run this command without sudo. Engineering Workshop installs into your own home folder."
  fi
  have curl || have wget || fail "Install curl, then run this command again."
  for tool in tar gzip awk sed; do
    have "$tool" || fail "This computer is missing the '$tool' command. Install it, then run this command again."
  done
  have sha256sum || have shasum || fail "This computer is missing the 'sha256sum' command. Install it, then run this command again."
}

prepare_home() {
  if { [ -e "$APP" ] || [ -e "$RUNTIME" ] || [ -e "$DATA" ]; } && [ ! -f "$MARKER" ]; then
    fail "$EW_HOME has files that this installer did not create. Set EW_HOME to another folder."
  fi
  mkdir -p "$EW_HOME" "$DATA" "$RUNTIME" || fail "Could not create $EW_HOME."
  say 'Created by the Engineering Workshop installer.' >"$MARKER"
  LOG=$EW_HOME/install.log
  : >"$LOG"
  log "Engineering Workshop installer, $(date), $OS-$ARCH"
  # Finish an update that stopped after moving the old app out.
  if [ -d "$OLD" ] && [ ! -d "$APP" ]; then mv "$OLD" "$APP"; fi
  rm -rf "$OLD" "$STAGE" "$WORK"
  mkdir "$WORK"
}

fetch_app() {
  if [ -n "${EW_ARCHIVE:-}" ]; then
    ARCHIVE=$EW_ARCHIVE
    [ -f "$ARCHIVE" ] || fail "EW_ARCHIVE points to a missing file: $ARCHIVE"
    SUMS=$(dirname "$ARCHIVE")/SHA256SUMS
    say "Using $ARCHIVE"
  else
    say "Downloading Engineering Workshop..."
    ARCHIVE=$WORK/engineering-workshop.tar.gz SUMS=$WORK/SHA256SUMS
    if ! download "$RELEASE_URL/engineering-workshop.tar.gz" "$ARCHIVE" ||
      ! download "$RELEASE_URL/SHA256SUMS" "$SUMS"; then
      fail "Could not download Engineering Workshop. Check your internet connection and try again."
    fi
  fi
  if [ -f "$SUMS" ]; then
    verify "$ARCHIVE" "$(basename "$ARCHIVE")" "$SUMS" || fail "The download is damaged. Run the command again."
  else
    log "No SHA256SUMS next to $ARCHIVE, so it was not checked."
  fi
  mkdir "$WORK/app"
  run tar -xzf "$ARCHIVE" -C "$WORK/app" || fail "Could not unpack $ARCHIVE."
  [ -f "$WORK/app/engineering-workshop/dist/index.html" ] ||
    fail "The download is incomplete. Run the command again."
  mv "$WORK/app/engineering-workshop" "$STAGE"
}

ensure_uv() {
  UV=$RUNTIME/uv/uv
  case $("$UV" --version 2>/dev/null || true) in "uv $UV_VERSION "*) return 0 ;; esac
  name=uv-$UV_TARGET.tar.gz
  url=https://github.com/astral-sh/uv/releases/download/$UV_VERSION/$name
  if ! download "$url" "$WORK/$name" || ! download "$url.sha256" "$WORK/$name.sha256"; then
    fail "Could not download uv, which installs Python. Check your internet connection and try again."
  fi
  verify "$WORK/$name" "$name" "$WORK/$name.sha256" || fail "The uv download is damaged. Run the command again."
  run tar -xzf "$WORK/$name" -C "$WORK" || fail "Could not unpack uv."
  mkdir -p "$RUNTIME/uv"
  mv -f "$WORK/uv-$UV_TARGET/uv" "$UV"
}

ensure_python() {
  say "Installing Python 3.12..."
  # Keep Python, packages and the download cache in the install folder. The new app/.venv
  # is built in a staging folder and moved into place, so it must be relocatable.
  export UV_PYTHON_INSTALL_DIR="$RUNTIME/python" UV_CACHE_DIR="$RUNTIME/cache" \
    UV_MANAGED_PYTHON=1 UV_NO_CONFIG=1 UV_VENV_RELOCATABLE=1
  unset PYTHONHOME PYTHONPATH VIRTUAL_ENV
  if [ "$OS" = linux ]; then
    # PyTorch from PyPI pulls in several GB of CUDA libraries that the lessons never use.
    export UV_TORCH_BACKEND=cpu
  fi
  ensure_uv
  run "$UV" python install 3.12 --no-bin --no-registry ||
    fail "Could not install Python 3.12. Check your internet connection and try again."
  PYTHON=$("$UV" python find 3.12 2>>"$LOG") || fail "Could not find the Python 3.12 that was just installed."
}

# scripts/setup.py creates app/.venv with this Python and installs the requirements with uv.
setup_packages() {
  run env PATH="$RUNTIME/uv:$PATH" "$PYTHON" "$STAGE/scripts/setup.py" --no-build --no-launch "$@"
}

install_packages() {
  light=${EW_LIGHT:-0}
  if [ "$light" = 1 ]; then
    say "Skipping the ML libraries (EW_LIGHT=1)."
  elif [ "$OS-$ARCH" = macos-x64 ]; then
    say "Skipping the ML libraries: PyTorch and TensorFlow no longer support Intel Macs."
    light=1
  else
    if ls -d "$APP"/.venv/lib/python3*/site-packages/torch >/dev/null 2>&1; then
      say "Updating the ML libraries..."
    else
      say "Downloading ML libraries (about 2 GB, this can take a while)..."
    fi
    if ! setup_packages; then
      say "Could not install the ML libraries, so they were skipped. Run this command again later to retry."
      rm -rf "$STAGE/.venv"
      light=1
    fi
  fi
  if [ "$light" = 1 ]; then
    say "$ML_NOTE"
    setup_packages --no-ml || fail "Could not install the Python packages. Check your internet connection and try again."
  fi
}

# True when $1 runs and is Node.js 22.13 or newer, the minimum in package.json.
node_ok() {
  node_version=$("$1" --version 2>/dev/null) || return 1
  node_version=${node_version#v}
  node_major=${node_version%%.*}
  node_minor=${node_version#*.}
  node_minor=${node_minor%%.*}
  case $node_major in '' | *[!0-9]*) return 1 ;; esac
  case $node_minor in '' | *[!0-9]*) return 1 ;; esac
  [ "$node_major" -gt 22 ] || { [ "$node_major" -eq 22 ] && [ "$node_minor" -ge 13 ]; }
}

# Choose how the app gets Node.js. Nothing in runtime/ changes until the app is stopped.
prepare_node() {
  NODE_PLAN=keep
  SYSTEM_NODE=$(command -v node 2>/dev/null || true)
  case $SYSTEM_NODE in "$RUNTIME"/* | '') SYSTEM_NODE= ;; esac
  if [ -n "$SYSTEM_NODE" ] && node_ok "$SYSTEM_NODE"; then
    # A link lets the app find it when opened from a launcher without your shell's PATH.
    log "Using $SYSTEM_NODE"
    NODE_PLAN=link
    return 0
  fi
  current=$RUNTIME/node/bin/node
  if [ -L "$current" ] || ! node_ok "$current"; then current=; fi
  base=https://nodejs.org/dist/latest-v$NODE_MAJOR.x
  name=
  if download "$base/SHASUMS256.txt" "$WORK/SHASUMS256.txt"; then
    name=$(awk -v target="$NODE_TARGET" '$2 ~ "^node-v[0-9.]+-" target "\\.tar\\.gz$" { print $2; exit }' "$WORK/SHASUMS256.txt")
  fi
  if [ -n "$name" ]; then
    version=${name#node-}
    if [ -n "$current" ] && [ "$("$current" --version)" = "${version%%-*}" ]; then return 0; fi
    say "Installing Node.js for the JavaScript lessons..."
    NODE_NEW=$WORK/node/${name%.tar.gz}
    if download "$base/$name" "$WORK/$name" && verify "$WORK/$name" "$name" "$WORK/SHASUMS256.txt" &&
      mkdir "$WORK/node" && run tar -xzf "$WORK/$name" -C "$WORK/node" && node_ok "$NODE_NEW/bin/node"; then
      NODE_PLAN=replace
      return 0
    fi
  fi
  if [ -n "$current" ]; then
    log "Kept Node.js $("$current" --version)."
  else
    say "Could not install Node.js, so the JavaScript lessons will not run. Run this command again later to retry."
  fi
}

stop_app() {
  if [ -x "$APP/.venv/bin/python" ] && [ -f "$APP/scripts/installed.py" ]; then
    run "$APP/.venv/bin/python" "$APP/scripts/installed.py" --stop || log "Could not stop the running app."
  fi
}

swap_in() {
  case $NODE_PLAN in
    link)
      rm -rf "$RUNTIME/node"
      mkdir -p "$RUNTIME/node/bin"
      ln -s "$SYSTEM_NODE" "$RUNTIME/node/bin/node"
      ;;
    replace)
      rm -rf "$RUNTIME/node"
      mv "$NODE_NEW" "$RUNTIME/node"
      ;;
  esac
  if [ -d "$APP" ]; then mv "$APP" "$OLD"; fi
  mv "$STAGE" "$APP"
  rm -rf "$OLD"
}

mac_app_id() {
  /usr/libexec/PlistBuddy -c 'Print :CFBundleIdentifier' "$1/Contents/Info.plist" 2>/dev/null || true
}

# True when the shortcut at $SHORTCUT was made by this installer for this install folder.
shortcut_is_ours() {
  if [ "$OS" = macos ]; then
    [ -d "$SHORTCUT" ] && [ "$(mac_app_id "$SHORTCUT")" = "$APP_ID" ] &&
      grep -qF "install=$(shell_quote "$EW_HOME")" "$SHORTCUT/Contents/MacOS/engineering-workshop" 2>/dev/null
  else
    [ -f "$SHORTCUT" ] && grep -qF "$(desktop_quote "$APP/scripts/installed.py")" "$SHORTCUT"
  fi
}

make_mac_app() {
  if [ -e "$SHORTCUT" ] && [ "$(mac_app_id "$SHORTCUT")" != "$APP_ID" ]; then
    say "Kept the other Engineering Workshop app in $(dirname "$SHORTCUT"); it was not replaced."
    return 0
  fi
  say "Adding Engineering Workshop to the Applications folder in your home folder..."
  contents=$WORK/bundle/Contents
  mkdir -p "$contents/MacOS" "$contents/Resources"
  cp "$APP/assets/Workshop.icns" "$contents/Resources/Workshop.icns"
  cat >"$contents/Info.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleDisplayName</key><string>Engineering Workshop</string>
  <key>CFBundleExecutable</key><string>engineering-workshop</string>
  <key>CFBundleIconFile</key><string>Workshop</string>
  <key>CFBundleIdentifier</key><string>$APP_ID</string>
  <key>CFBundleName</key><string>Engineering Workshop</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleShortVersionString</key><string>1.0</string>
  <key>CFBundleVersion</key><string>1</string>
  <key>LSMinimumSystemVersion</key><string>11.0</string>
</dict>
</plist>
EOF
  {
    say '#!/bin/sh'
    say '# Opens Engineering Workshop. Made by install.sh; run the installer again to recreate it.'
    say "install=$(shell_quote "$EW_HOME")"
    cat <<'EOF'
if [ -x "$install/app/.venv/bin/python" ]; then
  message=$("$install/app/.venv/bin/python" "$install/app/scripts/installed.py" 2>&1 >/dev/null) && exit 0
else
  message='Engineering Workshop is missing or damaged. Run the install command again.'
fi
/usr/bin/osascript - "${message:-See $install/data/server.log}" >/dev/null 2>&1 <<'END'
on run argv
  display alert "Engineering Workshop could not start" message (item 1 of argv) as critical
end run
END
EOF
  } >"$contents/MacOS/engineering-workshop"
  chmod 755 "$contents/MacOS/engineering-workshop"
  mkdir -p "$(dirname "$SHORTCUT")"
  rm -rf "$SHORTCUT"
  mv "$WORK/bundle" "$SHORTCUT"
  SHORTCUT_MADE=1
}

make_desktop_entry() {
  say "Adding Engineering Workshop to your applications menu..."
  mkdir -p "$(dirname "$SHORTCUT")"
  cat >"$SHORTCUT.tmp" <<EOF
[Desktop Entry]
Type=Application
Version=1.0
Name=Engineering Workshop
Comment=Practice ML and software engineering
Exec=$(desktop_quote "$APP/.venv/bin/python") $(desktop_quote "$APP/scripts/installed.py")
Icon=$APP/assets/Workshop.png
Terminal=false
Categories=Education;Development;
EOF
  mv "$SHORTCUT.tmp" "$SHORTCUT"
  SHORTCUT_MADE=1
}

make_shortcut() {
  SHORTCUT_MADE=0
  if [ "${EW_NO_SHORTCUTS:-0}" = 1 ]; then return 0; fi
  if [ "$OS" = macos ]; then make_mac_app; else make_desktop_entry; fi
}

finish() {
  rm -rf "$WORK"
  if [ "${EW_NO_LAUNCH:-0}" = 1 ]; then
    say "Done. Engineering Workshop is installed."
  else
    say "Starting Engineering Workshop..."
    errors=$EW_HOME/.launch-errors
    if url=$("$APP/.venv/bin/python" "$APP/scripts/installed.py" </dev/null 2>"$errors"); then
      rm -f "$errors"
      # The launcher prints the address with the session token after #. Show only the address.
      say "Done. Engineering Workshop is open in your browser at ${url%%#*}"
    else
      reason=$(cat "$errors")
      cat "$errors" >>"$LOG"
      rm -f "$errors"
      fail "Engineering Workshop is installed but did not start.
$reason"
    fi
  fi
  say "Your progress is saved in $DATA."
  if [ "$SHORTCUT_MADE" = 1 ] && [ "$OS" = macos ]; then
    say "To open it later, search for Engineering Workshop in Spotlight."
  elif [ "$SHORTCUT_MADE" = 1 ]; then
    say "To open it later, find Engineering Workshop in your applications menu."
  else
    say "To open it later, run: $(shell_quote "$APP/.venv/bin/python") $(shell_quote "$APP/scripts/installed.py")"
  fi
  say "To update, run the install command again."
}

install_app() {
  check_tools
  say "Installing Engineering Workshop in $EW_HOME"
  prepare_home
  fetch_app
  ensure_python
  install_packages
  prepare_node
  stop_app
  swap_in
  make_shortcut
  finish
}

uninstall_app() {
  if [ ! -f "$MARKER" ]; then
    say "Engineering Workshop is not installed in $EW_HOME."
    return 0
  fi
  LOG=$EW_HOME/install.log
  : >"$LOG"
  say "Removing Engineering Workshop..."
  stop_app
  if shortcut_is_ours; then rm -rf "$SHORTCUT"; fi
  rm -rf "$APP" "$RUNTIME" "$STAGE" "$OLD" "$WORK" || fail "Could not remove everything in $EW_HOME."
  if [ "$PURGE" = 1 ]; then
    rm -rf "$DATA" || fail "Could not remove $DATA."
    rm -f "$MARKER" "$LOG"
    rmdir "$EW_HOME" 2>/dev/null || true
    say "Removed Engineering Workshop and your progress."
  else
    rm -f "$LOG"
    say "Removed Engineering Workshop. Your progress is still in $DATA."
    say "To delete it too, run the uninstall command again with --purge at the end."
  fi
}

usage() {
  printf '%s\n' "Usage: install.sh [--uninstall [--purge]]" \
    "  Without options, install Engineering Workshop or update it and keep your progress." \
    "  --uninstall  Remove the app. Your progress stays in the data folder." \
    "  --purge      With --uninstall, also delete your progress."
}

main() {
  LOG=
  FAILED=0
  MODE=install_app
  PURGE=0
  trap on_exit EXIT
  for arg in "$@"; do
    case $arg in
      --uninstall) MODE=uninstall_app ;;
      --purge) PURGE=1 ;;
      -h | --help)
        usage
        return 0
        ;;
      *)
        usage >&2
        fail "Unknown option: $arg"
        ;;
    esac
  done
  if [ "$PURGE" = 1 ] && [ "$MODE" != uninstall_app ]; then fail "--purge only works together with --uninstall."; fi
  detect_platform
  set_paths
  "$MODE"
}

main "$@"
