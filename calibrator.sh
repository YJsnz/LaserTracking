#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="${BUILD_DIR:-$ROOT_DIR/src/build_full_auto}"
BIN="$BUILD_DIR/tool/boresight_calibrator/boresight_calibrator"

CAMERA_CONFIG="${CAMERA_CONFIG:-$ROOT_DIR/src/hik_camera/config/config.yaml}"
DETECTOR_CONFIG="${DETECTOR_CONFIG:-$ROOT_DIR/src/detector/config/detector.yaml}"
BORESIGHT_CONFIG="${BORESIGHT_CONFIG:-$ROOT_DIR/src/control/config/control.yaml}"
BORESIGHT_OUT="${BORESIGHT_OUT:-$ROOT_DIR/src/tool/boresight_calibrator/boresight.yaml}"

if [[ ! -x "$BIN" ]]; then
  echo "boresight_calibrator not found: $BIN" >&2
  echo "Build first: cd $ROOT_DIR/src && cmake -S . -B build_full_auto && cmake --build build_full_auto -j" >&2
  exit 1
fi

if [[ ! -f "$CAMERA_CONFIG" ]]; then
  echo "camera config not found: $CAMERA_CONFIG" >&2
  exit 1
fi

if [[ ! -f "$DETECTOR_CONFIG" ]]; then
  echo "detector config not found: $DETECTOR_CONFIG" >&2
  exit 1
fi

if [[ ! -f "$BORESIGHT_CONFIG" ]]; then
  echo "boresight config not found: $BORESIGHT_CONFIG" >&2
  exit 1
fi

exec "$BIN" \
  --camera-config "$CAMERA_CONFIG" \
  --detector-config "$DETECTOR_CONFIG" \
  --boresight-config "$BORESIGHT_CONFIG" \
  --boresight-out "$BORESIGHT_OUT" \
  "$@"
