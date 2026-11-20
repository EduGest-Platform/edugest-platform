#!/usr/bin/env bash
set -euo pipefail

if [[ $# != 2 || ! "$1" =~ ^[1-9][0-9]*$ ]]; then
  echo "Usage: bash review-worktree.sh PR_NUMBER NEW_WORKTREE_PATH" >&2
  exit 2
fi

pr=$1
destination=$2
if [[ -e "$destination" || -L "$destination" ]]; then
  echo "Choose a new worktree path: $destination already exists." >&2
  exit 2
fi

expected=$(gh pr view "$pr" --json headRefOid --jq .headRefOid)
base=$(gh pr view "$pr" --json baseRefName --jq .baseRefName)
git fetch --no-tags origin "refs/pull/$pr/head" "refs/heads/$base:refs/remotes/origin/$base"
actual=$(git rev-parse FETCH_HEAD)
if [[ "$actual" != "$expected" ]]; then
  echo 'The PR head changed during fetch. Read the new PR metadata and retry.' >&2
  exit 1
fi
git worktree add --detach "$destination" "$actual"
printf 'Review head: %s\nReview base: origin/%s\n' "$actual" "$base"
