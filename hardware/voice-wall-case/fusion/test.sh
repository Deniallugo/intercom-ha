#!/usr/bin/env bash
# Everything about the Fusion model that can be checked without opening Fusion.
#
#   1. design checks — params + electronics layout, pure CPython (vwc/checks.py)
#   2. build — every printed part through the adsk stand-in, each one body (tests/test_build.py)
#   3. sync — drag / sync / rebuild against an emulated document (tests/test_sync.py)
set -uo pipefail
cd "$(dirname "$0")"
PY="${PYTHON:-python3}"
fail=0

echo "== design checks =="
(cd VoiceWallCase && "$PY" vwc/checks.py) || fail=1
for t in test_build test_sync; do
  echo
  echo "== ${t#test_} =="
  if out=$(cd tests && "$PY" "$t.py" 2>&1); then echo "$out" | tail -1
  else echo "$out"; fail=1; fi
done
exit $fail
