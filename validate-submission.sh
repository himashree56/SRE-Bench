#!/usr/bin/env bash
#
# validate-submission.sh — SREBench OpenEnv Submission Validator
#
# Checks that your HF Space is live, Docker image builds, and openenv validate passes.
#
# Prerequisites:
#   - Docker Desktop (Windows): https://docs.docker.com/get-docker/
#   - openenv-core: pip install openenv-core
#   - Run in WSL2 or Git Bash on Windows
#
# Usage:
#   bash validate-submission.sh <ping_url> [repo_dir]
#
# Examples:
#   bash validate-submission.sh https://your-username-sre-bench.hf.space
#   bash validate-submission.sh https://your-username-sre-bench.hf.space ./sre-bench
#

set -uo pipefail

DOCKER_BUILD_TIMEOUT=600
DOCKER_IMAGE_NAME="sre-bench"

if [ -t 1 ]; then
  RED='\033[0;31m'
  GREEN='\033[0;32m'
  YELLOW='\033[1;33m'
  BOLD='\033[1m'
  NC='\033[0m'
else
  RED='' GREEN='' YELLOW='' BOLD='' NC=''
fi

run_with_timeout() {
  local secs="$1"; shift
  if command -v timeout &>/dev/null; then
    timeout "$secs" "$@"
  elif command -v gtimeout &>/dev/null; then
    gtimeout "$secs" "$@"
  else
    "$@" &
    local pid=$!
    ( sleep "$secs" && kill "$pid" 2>/dev/null ) &
    local watcher=$!
    wait "$pid" 2>/dev/null
    local rc=$?
    kill "$watcher" 2>/dev/null
    wait "$watcher" 2>/dev/null
    return $rc
  fi
}

portable_mktemp() {
  local prefix="${1:-validate}"
  mktemp "${TMPDIR:-/tmp}/${prefix}-XXXXXX" 2>/dev/null || mktemp
}

CLEANUP_FILES=()
cleanup() { rm -f "${CLEANUP_FILES[@]+"${CLEANUP_FILES[@]}"}"; }
trap cleanup EXIT

PING_URL="${1:-}"
REPO_DIR="${2:-.}"

if [ -z "$PING_URL" ]; then
  printf "Usage: %s <ping_url> [repo_dir]\n" "$0"
  printf "\n"
  printf "  ping_url   Your HuggingFace Space URL (e.g. https://your-username-sre-bench.hf.space)\n"
  printf "  repo_dir   Path to your repo (default: current directory)\n"
  printf "\n"
  printf "Examples:\n"
  printf "  bash validate-submission.sh https://your-username-sre-bench.hf.space\n"
  printf "  bash validate-submission.sh https://your-username-sre-bench.hf.space ./sre-bench\n"
  exit 1
fi

if ! REPO_DIR="$(cd "$REPO_DIR" 2>/dev/null && pwd)"; then
  printf "Error: directory '%s' not found\n" "${2:-.}"
  exit 1
fi

PING_URL="${PING_URL%/}"
export PING_URL
PASS=0

log()  { printf "[%s] %b\n" "$(date -u +%H:%M:%S)" "$*"; }
pass() { log "${GREEN}PASSED${NC} -- $1"; PASS=$((PASS + 1)); }
fail() { log "${RED}FAILED${NC} -- $1"; }
hint() { printf "  ${YELLOW}Hint:${NC} %b\n" "$1"; }
stop_at() {
  printf "\n"
  printf "${RED}${BOLD}Validation stopped at %s.${NC} Fix the above before continuing.\n" "$1"
  exit 1
}

printf "\n"
printf "${BOLD}========================================${NC}\n"
printf "${BOLD}  SREBench — OpenEnv Submission Validator${NC}\n"
printf "${BOLD}========================================${NC}\n"
log "Repo:     $REPO_DIR"
log "Ping URL: $PING_URL"
printf "\n"

# ── Step 1: Ping HF Space /reset ─────────────────────────────────────────────
log "${BOLD}Step 1/4: Pinging HF Space${NC} ($PING_URL/reset) ..."

CURL_OUTPUT=$(portable_mktemp "validate-curl")
CLEANUP_FILES+=("$CURL_OUTPUT")

HTTP_CODE=$(curl -s -o "$CURL_OUTPUT" -w "%{http_code}" -X POST \
  -H "Content-Type: application/json" \
  -d '{"task_name": "alert-classifier", "seed": 42}' \
  "$PING_URL/reset" --max-time 30 2>"$CURL_OUTPUT" || printf "000")

if [ "$HTTP_CODE" = "200" ]; then
  pass "HF Space is live and responds to /reset with task_name=alert-classifier"
elif [ "$HTTP_CODE" = "000" ]; then
  fail "HF Space not reachable (connection failed or timed out)"
  hint "Make sure your HF Space is running and public."
  hint "Try: curl -s -o /dev/null -w '%%{http_code}' -X POST $PING_URL/reset -H 'Content-Type: application/json' -d '{\"task_name\":\"alert-classifier\",\"seed\":42}'"
  stop_at "Step 1"
else
  fail "HF Space /reset returned HTTP $HTTP_CODE (expected 200)"
  hint "Check your Space logs at https://huggingface.co/spaces/your-username/sre-bench"
  hint "Common cause: server.py crashed on startup — check PYTHONPATH and openenv-core version."
  stop_at "Step 1"
fi

# ── Step 2: Verify /step responds ────────────────────────────────────────────
log "${BOLD}Step 2/4: Verifying /step endpoint${NC} ($PING_URL/step) ..."

STEP_OUTPUT=$(portable_mktemp "validate-step")
CLEANUP_FILES+=("$STEP_OUTPUT")

STEP_CODE=$(curl -s -o "$STEP_OUTPUT" -w "%{http_code}" -X POST \
  -H "Content-Type: application/json" \
  -d '{"action": {"tool": "list_alerts", "params": {}}}' \
  "$PING_URL/step" --max-time 30 2>"$STEP_OUTPUT" || printf "000")

if [ "$STEP_CODE" = "200" ]; then
  pass "/step endpoint responds correctly to list_alerts action"
else
  fail "/step returned HTTP $STEP_CODE (expected 200)"
  hint "Make sure /reset was called before /step — check session handling in server.py"
  hint "Action sent: {\"tool\": \"list_alerts\", \"params\": {}}"
  stop_at "Step 2"
fi

# ── Step 3: Docker build ───────────────────────────────────
log "${BOLD}Step 3/4: Testing local Docker build${NC} ..."

if ! command -v docker &>/dev/null; then
  fail "docker command not found"
  hint "Install Docker Desktop: https://docs.docker.com/get-docker/"
  stop_at "Step 3"
fi

# Test Docker build
DOCKER_BUILD_OK=false
DOCKER_BUILD_OUTPUT=$(cd "$REPO_DIR" && run_with_timeout "$DOCKER_BUILD_TIMEOUT" docker build -t sre-bench-test . 2>&1) && DOCKER_BUILD_OK=true

if [ "$DOCKER_BUILD_OK" = true ]; then
  pass "Docker build succeeded"
else
  fail "Docker build failed"
  printf "%s\n" "$DOCKER_BUILD_OUTPUT"
  hint "Check Dockerfile syntax and dependencies"
  hint "Ensure all required files are present"
  stop_at "Step 3"
fi

# ── Step 4: openenv validate ──────────────────────────────────────────────────
log "${BOLD}Step 4/4: Running openenv validate${NC} ..."

# if ! command -v openenv &>/dev/null; then
#   fail "openenv command not found"
#   hint "Install it: pip install openenv-core"
#   hint "Then re-run this script."
#   stop_at "Step 4"
# fi

VALIDATE_OK=false
# Cross-platform openenv validation
if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
  # Windows
  VALIDATE_OUTPUT=$(cd "$REPO_DIR" && venv/Scripts/openenv.exe validate 2>&1) && VALIDATE_OK=true
else
  # Unix-like (macOS, Linux)
  VALIDATE_OUTPUT=$(cd "$REPO_DIR" && source venv/bin/activate && openenv validate 2>&1) && VALIDATE_OK=true
fi

if [ "$VALIDATE_OK" = true ]; then
  pass "openenv validate passed"
  [ -n "$VALIDATE_OUTPUT" ] && log "  $VALIDATE_OUTPUT"
else
  fail "openenv validate failed"
  printf "%s\n" "$VALIDATE_OUTPUT"
  hint "Common causes: tasks use 'name:' instead of 'id:' in openenv.yaml"
  hint "Check reward_range covers negative values: [-0.5, 1.0]"
  hint "Verify all 3 endpoints (reset/step/state) respond correctly"
  stop_at "Step 4"
fi

# ── All checks passed ─────────────────────────────────────────────────────────
printf "\n"
printf "${BOLD}========================================${NC}\n"
printf "${GREEN}${BOLD}  All 4/4 checks passed!${NC}\n"
printf "${GREEN}${BOLD}  SREBench is ready to submit.${NC}\n"
printf "${BOLD}========================================${NC}\n"
printf "\n"
log "Next step: submit your HF Space URL at the hackathon portal."
printf "\n"

exit 0