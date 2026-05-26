#!/usr/bin/env bash
# Install CATalyst from a release .deb on Ubuntu/Debian.
# Uses apt so GTK/Qt/XCB/tray dependencies are pulled in automatically.
set -euo pipefail

deb_path="${1:-}"
if [[ -z "$deb_path" || ! -f "$deb_path" ]]; then
  echo "Usage: $0 catalyst_vVERSION_amd64.deb" >&2
  echo "Example: $0 ~/Downloads/catalyst_v1.2.38.3_amd64.deb" >&2
  exit 2
fi

deb_path="$(readlink -f "$deb_path")"

if ! command -v apt-get >/dev/null 2>&1; then
  echo "This installer requires apt (Ubuntu/Debian)." >&2
  exit 1
fi

echo "Installing CATalyst from $(basename "$deb_path") ..."
echo "(Using apt so dependencies are installed — do not use dpkg -i alone.)"
echo

sudo apt-get update -qq
if dpkg-query -W catalyst >/dev/null 2>&1; then
  st="$(dpkg-query -W -f='${Status}' catalyst 2>/dev/null || true)"
  case "$st" in
    *"install ok installed"*) ;;
    *)
      echo "Repairing broken catalyst package state ..."
      sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -f
      ;;
  esac
fi

sudo DEBIAN_FRONTEND=noninteractive apt-get install -y "$deb_path"

echo
echo "Installed. Verify:"
dpkg -l catalyst | tail -1 || true
if [[ -f /opt/catalyst/linux-desktop-loopback-fix.txt ]]; then
  cat /opt/catalyst/linux-desktop-loopback-fix.txt
fi
echo "Run: catalyst"
