#!/usr/bin/env bash
set -uo pipefail
OPENSCAD="${OPENSCAD:-$(command -v openscad || echo /Applications/OpenSCAD-2021.01.app/Contents/MacOS/OpenSCAD)}"
[ -x "$OPENSCAD" ] || { echo "OpenSCAD not found (set \$OPENSCAD)"; exit 1; }
cd "$(dirname "$0")"
mkdir -p stl
fail=0

echo "== parameter asserts =="
"$OPENSCAD" --hardwarnings -o /tmp/kc_asserts.stl tests/asserts.scad >/dev/null 2>&1 \
    && echo "OK asserts" || { echo "FAIL asserts"; fail=1; }

for part in front rear button coupon spacer; do
    if "$OPENSCAD" --hardwarnings -D "part=\"$part\"" -o "stl/$part.stl" kitchen-case.scad 2>/tmp/kc_err; then
        sz=$(wc -c < "stl/$part.stl")
        if [ "$sz" -lt 1000 ]; then echo "FAIL $part: STL too small ($sz B)"; fail=1
        else echo "OK $part ($sz B)"; fi
    else
        echo "FAIL $part render:"; cat /tmp/kc_err; fail=1
    fi
done
exit $fail
