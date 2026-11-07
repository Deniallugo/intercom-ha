#!/usr/bin/env bash
set -uo pipefail
OPENSCAD="${OPENSCAD:-$(command -v openscad || echo /Applications/OpenSCAD-2021.01.app/Contents/MacOS/OpenSCAD)}"
[ -x "$OPENSCAD" ] || { echo "OpenSCAD not found (set \$OPENSCAD)"; exit 1; }
cd "$(dirname "$0")"
mkdir -p stl
tmp="${TMPDIR:-/tmp}"
fail=0

echo "== design checks =="
if "$OPENSCAD" --hardwarnings -o "$tmp/vwc_asserts.stl" tests/asserts.scad 2>"$tmp/vwc_err"; then
    echo "OK asserts"; grep '^ECHO' "$tmp/vwc_err" | sed 's/^ECHO: "/   /; s/"$//'
else
    echo "FAIL asserts"; grep -E 'ERROR|WARNING|assert' "$tmp/vwc_err"; fail=1
fi

PARTS="amp-shell amp-lid amp-sled voice-shell voice-lid voice-tray sleeve plunger dome holder clamp plate lock coupon-amp coupon-voice"
for part in $PARTS; do
    if "$OPENSCAD" --hardwarnings -D "part=\"$part\"" -o "stl/$part.stl" voice-wall-case.scad 2>"$tmp/vwc_err"; then
        sz=$(wc -c < "stl/$part.stl")
        if [ "$sz" -lt 1000 ]; then echo "FAIL $part: STL too small ($sz B)"; fail=1
        else echo "OK $part ($sz B)"; fi
    else
        echo "FAIL $part render:"; cat "$tmp/vwc_err"; fail=1
    fi
done
exit $fail
