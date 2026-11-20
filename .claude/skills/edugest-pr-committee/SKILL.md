---
name: edugest-pr-committee
description: Review an EduGest pull request, branch or pasted diff as a 5-member committee (product, security, code, tests, UX) and return a verdict plus a ready-to-paste GitHub comment. Use for 'review this PR', 'self-review', or a pasted diff.
---

# EduGest PR committee

Review a change the way a small, fair committee would: five reviewers, each with one focus, one combined verdict. The review **advises**. A human always approves and merges.

## Hard rules (never break)

- **Advise only.** Never approve, request changes, merge, push, comment on GitHub or edit Jira. The user posts the comment themselves.
- **Verify in isolation.** Local checks run only in a separate review worktree made by `scripts/review-worktree.sh`. Never check out over someone's working branch. Never use the dev database or a real `.env`; synthetic data only; Python dependencies in a throwaway virtualenv.
- **Read before you run.** If the PR adds or changes a script (`*.sh`, `scripts/`, `package.json` scripts, migrations), read it before running any check.
- **Say what you verified.** Every check is PASS, FAIL or NOT RUN with a reason. Not run = not verified. Never call something green that you did not see pass.
- **Only the change.** Review the lines that changed and what they directly affect. No rewriting whole files. No style comments the linter (ruff, oxfmt) already covers.
- **Respect owners.** Suggest, never edit, other people's areas: Elizabeth = API/DB/contracts, Anas = frontend, David = RAG/feedback, Abdur = dropout ML only, Yohanna = automation/CI. Do not reassign work.
- **Synthetic data only.** Flag anything that loads, logs or asks for real student data.
- **Kind tone.** Start with what is good. Explain *why*, show the fix, never blame.

## Step 1 · Gather the change

Accept any of: a PR number or URL, a branch name, or a pasted diff.

- PR: `gh pr view <n> --json title,body,author,headRefName,baseRefName,headRefOid,files,additions,deletions`, then `gh pr diff <n>` and `gh pr checks <n>`.
- Branch: compare with its **real base**, not always `dev`. Stacked PRs (for example #46 on top of #40) must be compared with the parent branch, or the parent's changes are blamed on the child.
  1. Base given by the user → use it.
  2. Else the base of the open PR for that branch: `gh pr list --head <branch> --json baseRefName`.
  3. Else `dev`, and say in the report that the base was assumed and the user can give another.

  Then `git fetch origin`, `git diff origin/<base>...origin/<branch>` and `git log origin/<base>..origin/<branch> --oneline`.
- Pasted diff: use it as-is. Say lines may be cut off; mark anything you cannot see as "please confirm" instead of guessing. Local checks are NOT RUN (no code to run).

If `gh` is not logged in, fall back to git, or ask for the diff.

## Step 2 · Read the project rules

Read the parts that apply to this change: `CONSTITUTION.md`, `AGENTS.md`, `CLAUDE.md`, `contribution.md`, `projectplan.md` (dates, guardrails). Find the Jira key (KAN-xx) in the branch, title or body. If the Jira tools are available, read that ticket's summary and acceptance criteria. Never change it.

## Step 3 · Size check

If the change is over ~400 changed lines (ignoring lockfiles and generated `schema.gen.ts`), say so first and suggest how to split it. If the diff is mostly line-ending noise (CRLF/LF), say that and stop.

## Step 4 · Verify locally

Some problems only show up when you run the code (for example a focus ring with too little contrast that no test or CI catches). Use the scripts next to this skill, so every teammate runs the same checks. Do not improvise other commands.

1. **Isolate:** `.claude/skills/edugest-pr-committee/scripts/review-worktree.sh <pr-number|branch> [base]`. It fetches the PR into `review/pr-<n>`, makes a worktree next to the repository, chooses the base (yours, then GitHub's, then `dev` with a warning), prints the **reviewed SHA** and says which checks apply. Write the SHA in the report.
2. **Run the checks for the type of change.** Mixed PRs use the strictest row.

| Change | Local verification |
|---|---|
| Docs only (`*.md`, `docs/`) | Read only; check the document's claims against the base with `git grep <term> origin/<base>` |
| Web (`src/`, `package.json`, Vite config) | `scripts/review-web.sh <worktree>`: install with the lockfile, `tsc`, `pnpm test`, `pnpm build`, API types up to date. If colours change: `node scripts/contrast.mjs <colour> <background>` for every new pair, including dark areas like the navy sidebar |
| API / DB (`api/`, `alembic/`, `contracts/`) | `scripts/review-api.sh <worktree>`: local Docker only; throwaway `pgvector/pgvector:pg16` on a free port Docker picks on `127.0.0.1`, and Alembic and pytest use the URL built from that container's port, so the downgrade only touches this review's database. Throwaway virtualenv, `ruff`, `alembic upgrade head && alembic check && alembic downgrade base && alembic upgrade head`, `pytest`. The script removes only the container it created |
| CI / infra (`.github/`, `infra/`, Dockerfile, `render.yaml`) | Careful read; `scripts/review-ci.sh <worktree>` (`docker compose config` with the example env file) |

3. **Clean up:** `scripts/review-cleanup.sh <worktree>` only accepts a worktree made by `review-worktree.sh`, stops if it has any change, and removes it and its `review/` branch without forcing (if git will not delete the branch, it is kept and the script says so). Database containers are not its job: `review-api.sh` removes its own.

If a tool is missing (no Docker, no pnpm, no network), the check is NOT RUN with that reason. Never replace it with a guess.

## Step 5 · The five reviewers

Run each reviewer on the change, using what Step 4 showed. For big or risky PRs (auth, RBAC, admission decision, enrolment, CI/secrets), run each reviewer as a separate subagent that does not see the others' notes, then merge. For small PRs, do them yourself in order.

**1. Product and briefing**
- Does it do what its Jira ticket says? Is the KAN key there?
- Matches the briefing and `projectplan.md` guardrails: human decision on admission (no automatic rejection), attendance 1 / 0.5, AI and risk shown as suggestions only.
- No mock shown as real (for example, nothing called "RAG" while it is still a mock).

**2. Security and privacy**
- Permissions checked in the backend by role + programme/cohort, deny by default. Hidden buttons are not protection. Look for horizontal access (IDOR).
- No secrets, tokens or default passwords in code, `.env.example`, logs or CI. Tokens never in `localStorage`.
- No personal data in URLs, logs or error messages. No `dangerouslySetInnerHTML`. External links use `rel="noopener noreferrer"`.
- Network calls: no following redirects with credentials, timeouts set.

**3. Code quality**
- A human can understand it: clear English names, small single-purpose functions, no dead code, no clever tricks.
- Fits the structure: `src/`, `api/`, `contracts/`, `e2e/`, `infra/`. Frontend keeps Vite, Tailwind v4 in `src/index.css`, `.figma/`, aliases. No Next or Astro.
- API types generated from `contracts/openapi.json` (`pnpm gen:api`), not written by hand.

**4. Tests and evidence**
- CI green (`gh pr checks`). If not, which job and why.
- Local checks from Step 4 match CI. If they differ, say so.
- New logic has tests. Permission changes have one positive and one negative test.
- The PR says which commands were run and their result. Missing evidence = blocked, not green.

**5. UX and accessibility** (only if `src/` changed)
- Works with the keyboard; labels on every field; visible focus on every background (light and dark); good contrast.
- Plain Spanish UI text using *tú*; errors say what to do next.
- Empty, loading and 401/403 states exist. No dead ends.
- Respects `prefers-reduced-motion`.

## Step 6 · Check before you report

For every finding, look at the actual code again and confirm it is real. Drop anything you cannot confirm, or mark it "please confirm". Merge duplicates from different reviewers. Fewer, true findings beat many guesses.

## Step 7 · Output

Use exactly this shape, in the user's language (English or Spanish):

```
**Verdict:** ✅ Approve | 🟡 Approve with small fixes | 🔴 Changes needed
**Reviewed:** <SHA> compared with origin/<base> (<how the base was chosen>)

| Check | Command | Result |
|---|---|---|
| ... | ... | PASS / FAIL / NOT RUN: reason |

**What's good:** 1–3 lines

**Must fix** (blocks merge): file:line · problem · why · fix
**Should fix** (small, worth doing now): ...
**Follow-ups** (later, suggested Jira ticket for each): ...

**Committee scores (1–5):** Product · Security · Code · Tests · UX (or n/a)
```

Then a **ready-to-paste GitHub comment**: short, friendly, starts with thanks or what is good, lists must-fix items with code snippets, includes the checks table, ends with follow-ups. Mention people only by their real GitHub handle when the user gave it.

## Self-review mode

If the user asks to review their *own* work before opening a PR, use the same steps (Step 4 can run on their branch with `review-worktree.sh <branch> <base>`) but write the output as a to-do list for them, and skip the GitHub comment.
