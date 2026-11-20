#!/usr/bin/env bash
# Remove a review worktree and its review/ branch when the review is done.
# Usage: review-cleanup.sh <worktree>
set -euo pipefail
worktree="${1:?Give the worktree path printed by review-worktree.sh}"
repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"

branch="review/$(basename "$worktree" | sed 's/^edugest-review-//')"
git worktree remove --force "$worktree"
git worktree prune
if git show-ref --verify --quiet "refs/heads/$branch"; then
  git branch -D "$branch" >/dev/null
fi
if command -v docker >/dev/null 2>&1; then
  docker ps --all --quiet --filter "name=edugest-review-db-" 2>/dev/null | xargs -r docker rm --force >/dev/null 2>&1 || true
fi
echo "Removed $worktree and $branch."
