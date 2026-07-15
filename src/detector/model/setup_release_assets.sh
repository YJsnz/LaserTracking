#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
DEST_DIR="${SCRIPT_DIR}"

SOURCE_DIR=""
COPY_MODE="copy"

usage() {
  cat <<EOF
Usage: $(basename "$0") --source /path/to/release-assets [--link]

Copies or symlinks detector model assets into:
  ${DEST_DIR}

Expected asset names:
  best_fp16.engine
  best_int8.engine
  best.onnx
  best_raw.onnx
  ball.onnx
  ball.pt
  calib.bin

Examples:
  $(basename "$0") --source ~/Downloads/LaserTracking-2026-assets
  $(basename "$0") --source ~/Downloads/LaserTracking-2026-assets --link
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --source)
      SOURCE_DIR="$2"
      shift 2
      ;;
    --link)
      COPY_MODE="link"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "[ERROR] Unknown arg: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if [[ -z "${SOURCE_DIR}" ]]; then
  echo "[ERROR] --source is required" >&2
  usage
  exit 1
fi

if [[ ! -d "${SOURCE_DIR}" ]]; then
  echo "[ERROR] Source dir not found: ${SOURCE_DIR}" >&2
  exit 1
fi

find_one() {
  local name="$1"
  find "${SOURCE_DIR}" -type f -name "${name}" -print -quit 2>/dev/null || true
}

install_one() {
  local name="$1"
  local src
  src="$(find_one "${name}")"
  if [[ -z "${src}" ]]; then
    echo "[MISS] ${name}"
    return 1
  fi

  local dst="${DEST_DIR}/${name}"
  rm -f "${dst}"
  if [[ "${COPY_MODE}" == "link" ]]; then
    ln -s "${src}" "${dst}"
    echo "[LINK] ${name} <- ${src}"
  else
    cp -f "${src}" "${dst}"
    echo "[COPY] ${name} <- ${src}"
  fi
  return 0
}

required=(
  "best_fp16.engine"
)

optional=(
  "best_int8.engine"
  "best.onnx"
  "best_raw.onnx"
  "ball.onnx"
  "ball.pt"
  "calib.bin"
)

missing_required=0

for name in "${required[@]}"; do
  if ! install_one "${name}"; then
    missing_required=1
  fi
done

for name in "${optional[@]}"; do
  install_one "${name}" || true
done

echo
echo "[INFO] Installed assets in ${DEST_DIR}"
echo "[INFO] TRT config expects: ${DEST_DIR}/best_fp16.engine"

if [[ "${missing_required}" -ne 0 ]]; then
  echo "[ERROR] Missing required asset(s). See ${DEST_DIR}/README.md" >&2
  exit 1
fi

echo "[OK] Required assets are in place."
echo "[NEXT] Try:"
echo "  cd ${SCRIPT_DIR}/../../build_full_auto/detector && ./detector_demo --config ../../detector/config/detector.yaml --video ../../../docs/demo.gif --no-show"
