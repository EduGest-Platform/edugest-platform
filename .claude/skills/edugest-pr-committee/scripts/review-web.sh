#!/usr/bin/env bash
set -euo pipefail

# Run from the root of the detached review worktree.
pnpm install --frozen-lockfile
pnpm exec tsc --noEmit -p tsconfig.json
pnpm test
pnpm build
