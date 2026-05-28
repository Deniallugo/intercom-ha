#!/usr/bin/env bash
# Flash an ESPHome device from this repo.
#
# Usage:
#   ./flash.sh <device>            # auto-detect (OTA over mDNS or USB if plugged in)
#   ./flash.sh <device> <target>   # explicit USB path or .local hostname
#   ./flash.sh                     # list available devices
#
# Examples:
#   ./flash.sh intercom-s3                              # auto
#   ./flash.sh intercom-s3 /dev/cu.usbserial-0001       # USB
#   ./flash.sh atom-echo atom-echo-7a3b.local           # OTA
#   ./flash.sh intercom-s3 OTA                          # force OTA path

set -euo pipefail

cd "$(dirname "$0")"

DEVICES_DIR="devices"

list_devices() {
    echo "Available devices:"
    for f in "$DEVICES_DIR"/*.yaml; do
        name="$(basename "$f" .yaml)"
        [[ "$name" == "secrets" ]] && continue
        echo "  $name"
    done
}

if [[ $# -lt 1 ]]; then
    list_devices
    echo
    echo "Usage: $0 <device> [target]"
    exit 1
fi

DEVICE="$1"
YAML="$DEVICES_DIR/${DEVICE}.yaml"

if [[ ! -f "$YAML" ]]; then
    echo "Error: $YAML not found"
    echo
    list_devices
    exit 1
fi

if [[ $# -ge 2 ]]; then
    exec esphome run "$YAML" --device "$2"
else
    exec esphome run "$YAML"
fi
