#!/usr/bin/env bash
# Everything about this port that can be checked without opening Fusion.
#
#   1. the design checks — pure CPython, the port of tests/asserts.scad
#   2. the geometry itself — the port's own build code run against an adsk stand-in that
#      emits OpenSCAD, rendered, and diffed against ../stl/*.stl. Skipped if OpenSCAD is
#      not installed; run ../build.sh first if the reference STLs are missing.
set -uo pipefail
cd "$(dirname "$0")"
PY="${PYTHON:-python3}"
fail=0

echo "== design checks =="
(cd VoiceCase && "$PY" vc/checks.py) || fail=1

echo
echo "== geometry vs OpenSCAD =="
(cd tests && "$PY" render_diff.py "$@") || fail=1

exit $fail
