#!/usr/bin/env bash
# CI and infrastructure checks for a PR worktree. Most of this is careful reading;
# this script only checks that the Docker Compose file is valid.
# Usage: review-ci.sh <worktree>
set -uo pipefail
worktree="${1:?Give the worktree path printed by review-worktree.sh}"
source "$(dirname "$0")/report.sh"
cd "$worktree" || exit 1

report_header
if command -v docker >/dev/null 2>&1; then
  # Use the example env file so no real secrets are read.
  if [[ -f infra/.env.example ]]; then
    run_check "compose file" "docker compose --env-file infra/.env.example -f infra/compose.yaml config --quiet"
  else
    run_check "compose file" "docker compose -f infra/compose.yaml config --quiet"
  fi
else
  not_run "compose file" "docker compose -f infra/compose.yaml config --quiet" "Docker is not installed"
fi
echo
echo "Read by hand: .github/workflows/*.yml (secrets, permissions, pinned actions), Dockerfile, render.yaml."
exit "$FAILED"
