#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ENTRY="$ROOT/scripts/devkit.py"
if [ -f "$ROOT/worker/scripts/devkit.py" ]; then ENTRY="$ROOT/worker/scripts/devkit.py"; fi
if [ "$#" -eq 0 ]; then set -- wizard; fi
exec python3 "$ENTRY" "$@"
