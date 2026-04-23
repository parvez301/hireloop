#!/usr/bin/env bash
# Visual-regression capture: live routes + prototype HTML files.
# Output: /tmp/hl-screens/{live,proto}/*.png + /tmp/hl-screens/errors.json
# After running: open user-portal/tools/compare.html
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORTAL_DIR="$(cd "${HERE}/.." && pwd)"
PORT=5173
OUT_DIR=/tmp/hl-screens

cleanup_port() {
  local pids
  pids=$(lsof -ti tcp:${PORT} 2>/dev/null || true)
  if [[ -n "${pids}" ]]; then
    echo "[screenshot] killing existing processes on :${PORT}: ${pids}"
    kill -9 ${pids} 2>/dev/null || true
    sleep 1
  fi
}

wait_for_port() {
  local tries=0
  while (( tries < 60 )); do
    if curl -sSf "http://localhost:${PORT}/" -o /dev/null 2>/dev/null; then
      return 0
    fi
    sleep 0.5
    tries=$((tries + 1))
  done
  return 1
}

mkdir -p "${OUT_DIR}/live" "${OUT_DIR}/proto"

cleanup_port

pushd "${PORTAL_DIR}" >/dev/null

echo "[screenshot] starting vite dev on :${PORT}..."
DEV_LOG="${OUT_DIR}/vite.log"
: > "${DEV_LOG}"
pnpm dev >"${DEV_LOG}" 2>&1 &
DEV_PID=$!

trap '[[ -n "${DEV_PID:-}" ]] && kill ${DEV_PID} 2>/dev/null; cleanup_port' EXIT

if ! wait_for_port; then
  echo "[screenshot] vite failed to answer on :${PORT}. Tail of ${DEV_LOG}:"
  tail -30 "${DEV_LOG}" || true
  exit 2
fi

echo "[screenshot] running playwright spec..."
npx playwright test e2e/screenshots.spec.ts --project=chromium --reporter=dot --no-deps
RC=$?

popd >/dev/null

echo
echo "[screenshot] done (exit ${RC}). Results in ${OUT_DIR}"
echo "[screenshot] open user-portal/tools/compare.html"
exit ${RC}
