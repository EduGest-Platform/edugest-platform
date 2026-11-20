#!/usr/bin/env bash
# Prepare an isolated, read-only copy of a PR or branch for review.
#
# Usage:
#   review-worktree.sh <pr-number>            # base taken from GitHub (gh), else asks for it
#   review-worktree.sh <pr-number> <base>     # base given by you (for example a stacked PR)
#   review-worktree.sh <branch> [<base>]      # same, starting from a branch name
#
# It never checks out over your working branch: the copy lives in a separate
# git worktree next to the repository. Remove it with review-cleanup.sh.
set -euo pipefail

target="${1:?Give a PR number or a branch name}"
base_arg="${2:-}"

repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"

git fetch --quiet origin

# 1. Get the code under review into a local review/ branch.
if [[ "$target" =~ ^[0-9]+$ ]]; then
  review_branch="review/pr-$target"
  git fetch --quiet --force origin "pull/$target/head:$review_branch"
  gh_base=""
  if command -v gh >/dev/null 2>&1; then
    gh_base="$(gh pr view "$target" --json baseRefName --jq .baseRefName 2>/dev/null || true)"
  fi
else
  review_branch="review/${target//\//-}"
  git branch --force "$review_branch" "origin/$target" >/dev/null
  gh_base=""
  if command -v gh >/dev/null 2>&1; then
    gh_base="$(gh pr list --head "$target" --json baseRefName --jq '.[0].baseRefName' 2>/dev/null || true)"
  fi
fi

# 2. Choose the base. Your argument wins, then GitHub, then dev (with a warning).
#    Stacked PRs (for example #46 on top of #40) must use the parent branch,
#    or the parent's changes are blamed on the child.
if [[ -n "$base_arg" ]]; then
  base="$base_arg"; base_source="given by you"
elif [[ -n "$gh_base" ]]; then
  base="$gh_base"; base_source="from GitHub"
else
  base="dev"; base_source="DEFAULT - could not read the PR base; pass it as 2nd argument if this is a stacked PR"
fi
git rev-parse --verify --quiet "origin/$base" >/dev/null || {
  echo "Base branch origin/$base does not exist. Pass the right base as 2nd argument." >&2
  exit 1
}

# 3. Create the worktree outside the repository folder.
worktree="$(dirname "$repo_root")/edugest-${review_branch//\//-}"
if [[ -e "$worktree" ]]; then
  echo "$worktree already exists. Run review-cleanup.sh $worktree first." >&2
  exit 1
fi
git worktree add --quiet --detach "$worktree" "$review_branch"

head_sha="$(git rev-parse "$review_branch")"
merge_base="$(git merge-base "origin/$base" "$review_branch")"

echo "Reviewed SHA : $head_sha"
echo "Base         : origin/$base ($base_source)"
echo "Merge base   : $merge_base"
echo "Worktree     : $worktree"
echo
echo "Changed files (compared with the merge base):"
git diff --stat "$merge_base" "$head_sha" | tail -n 25
echo
echo "Commits in this change:"
git log --oneline "$merge_base..$head_sha"
echo

# 4. Suggest which checks apply. Mixed changes use the strictest row.
files="$(git diff --name-only "$merge_base" "$head_sha")"
needs=()
grep -qE '^(src/|index\.html|vite\.config\.ts|package\.json|pnpm-lock\.yaml|tsconfig)' <<<"$files" && needs+=("web: review-web.sh $worktree")
grep -qE '^(api/|contracts/)' <<<"$files" && needs+=("api: review-api.sh $worktree")
grep -qE '^(\.github/|infra/|Dockerfile|render\.yaml|docker-compose)' <<<"$files" && needs+=("ci/infra: review-ci.sh $worktree")
if [[ ${#needs[@]} -eq 0 ]]; then
  needs+=("docs only: read the files; check their claims with git grep <term> origin/$base")
fi
echo "Checks to run:"
printf '  - %s\n' "${needs[@]}"
echo
echo "Before running anything, read any new or changed script in the PR (scripts/, *.sh, package.json scripts)."
