#!/usr/bin/env bash
set -euo pipefail
OPENSCAD="${OPENSCAD:-$(command -v openscad || echo /Applications/OpenSCAD-2021.01.app/Contents/MacOS/OpenSCAD)}"
[ -x "$OPENSCAD" ] || { echo "OpenSCAD not found (set \$OPENSCAD)"; exit 1; }
cd "$(dirname "$0")"
mkdir -p stl
for part in shell base button holder clamp fit fit-front; do
    echo "rendering $part ..."
    "$OPENSCAD" -D "part=\"$part\"" -o "stl/$part.stl" voice-case.scad
done
echo "done -> stl/"
