#!/usr/bin/env bash
# Web checks for a PR worktree made by review-worktree.sh. Same commands as CI.
# Usage: review-web.sh <worktree>
set -uo pipefail
worktree="${1:?Give the worktree path printed by review-worktree.sh}"
source "$(dirname "$0")/report.sh"
cd "$worktree" || exit 1

if [[ -e .env || -e .env.local ]]; then
  echo "This worktree has a .env file. Remove it: reviews never use real settings." >&2
  exit 1
fi

report_header
if ! command -v pnpm >/dev/null 2>&1; then
  not_run "install" "pnpm install --frozen-lockfile" "pnpm is not installed"
  exit 1
fi
run_check "install" "pnpm install --frozen-lockfile"
run_check "types" "pnpm exec tsc --noEmit -p ."
run_check "tests" "pnpm test"
run_check "build" "pnpm build"
run_check "api types up to date" "pnpm gen:api && git diff --exit-code src/shared/api/schema.gen.ts"

# Colours changed? Then contrast must be checked with contrast.mjs.
echo
echo "If the PR changes colours (src/index.css, bg-/text-/border- classes), run for each new pair:"
echo "  node $(dirname "$0")/contrast.mjs <text-or-ring-colour> <background-colour>"
echo "Text needs 4.5:1, large text and focus rings 3:1. Include dark areas like the navy sidebar."
echo
echo "Logs: $LOG_DIR"
exit "$FAILED"
