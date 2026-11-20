#!/usr/bin/env bash
# Remove a review worktree made by review-worktree.sh, and its review/ branch.
# Safe by design:
#   - only accepts a worktree that review-worktree.sh created (location, name,
#     registered in this repository, and still on its review/ branch commit);
#   - stops if the worktree has any change, including untracked files;
#   - never forces: git refuses to delete anything that is not safe to delete.
# Database containers are not touched here: review-api.sh removes its own.
# Usage: review-cleanup.sh <worktree>
set -euo pipefail

stop() {
  echo "Cleanup stopped: $1" >&2
  exit 1
}

worktree_arg="${1:?Give the worktree path printed by review-worktree.sh}"
repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"

# 1. The path must be a worktree of this repository.
[[ -d "$worktree_arg" ]] || stop "$worktree_arg is not a folder."
worktree="$(git -C "$worktree_arg" rev-parse --show-toplevel 2>/dev/null)" \
  || stop "$worktree_arg is not a git worktree."
git worktree list --porcelain | grep -qxF "worktree $worktree" \
  || stop "$worktree is not a worktree of this repository."

# 2. It must be where and how review-worktree.sh creates it.
name="$(basename "$worktree")"
[[ "$name" == edugest-review-* ]] \
  || stop "$worktree was not created by review-worktree.sh (name must start with edugest-review-)."
[[ "$(dirname "$worktree")" == "$(dirname "$repo_root")" ]] \
  || stop "$worktree is not next to the repository, where review-worktree.sh creates it."

branch="review/${name#edugest-review-}"
git show-ref --verify --quiet "refs/heads/$branch" \
  || stop "the review branch $branch does not exist, so $worktree cannot be matched to a review."
[[ "$(git -C "$worktree" rev-parse HEAD)" == "$(git rev-parse "$branch")" ]] \
  || stop "$worktree is not on the commit of $branch any more. Check it by hand."

# 3. Never throw work away.
changes="$(git -C "$worktree" status --porcelain --untracked-files=all)"
if [[ -n "$changes" ]]; then
  echo "$changes" >&2
  stop "$worktree has changes (listed above). Save or discard them yourself, then run this again."
fi

# 4. Remove without forcing.
git worktree remove "$worktree"
git worktree prune
echo "Removed $worktree."

if git branch -d "$branch" >/dev/null 2>&1; then
  echo "Removed $branch."
else
  echo "Kept $branch: git does not see it as merged. It is only a local copy of the PR;"
  echo "delete it yourself when you are sure: git branch -D $branch"
fi
