#!/usr/bin/env bash
# Everything about the Fusion model that can be checked without opening Fusion.
#
#   1. design checks — params + electronics layout, pure CPython (vwc/checks.py)
#   2. sync — drag / sync / rebuild against an emulated document (tests/test_sync.py)
#   3. geometry — the port's own build code emitted as OpenSCAD, rendered, and diffed against
#      ../voice-wall-case.scad rendered with the same placement (tests/render_diff.py).
#      Skipped without OpenSCAD. Extra flags go to render_diff: --quick, --interference,
#      --picture, --png, or part names.
set -uo pipefail
cd "$(dirname "$0")"
PY="${PYTHON:-python3}"
fail=0

echo "== design checks =="
(cd VoiceWallCase && "$PY" vwc/checks.py) || fail=1
echo
echo "== sync =="
if out=$(cd tests && "$PY" test_sync.py 2>&1); then echo "$out" | tail -1
else echo "$out"; fail=1; fi
echo
(cd tests && "$PY" render_diff.py "$@") || fail=1
exit $fail
