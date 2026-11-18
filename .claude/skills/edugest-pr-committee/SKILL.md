---
name: "edugest-pr-committee"
description: "Review an EduGest pull request, branch or pasted diff as a 5-member committee (product, security, code, tests, UX) and return a verdict plus a ready-to-paste GitHub comment. Use for 'review this PR', 'self-review', or a pasted diff."
---

# EduGest PR committee

Review a change the way a small, fair committee would: five reviewers, each with one focus, one combined verdict. The review **advises**. A human always approves and merges.

## Hard rules (never break)

- **Read-only.** Never approve, request changes, merge, push, comment on GitHub or edit Jira. Only use read-only commands (`gh pr view`, `gh pr diff`, `gh pr checks`, `git diff`, `git log`). The user posts the comment themselves.
- **Say what you verified.** Write "read the diff" or "ran `pytest`" for each claim. Not run = not verified. Never call something green that you did not see pass.
- **Only the change.** Review the lines that changed and what they directly affect. No rewriting whole files. No style comments the linter (ruff, oxfmt) already covers.
- **Respect owners.** Suggest, never edit, other people's areas: Elizabeth = API/DB/contracts, Anas = frontend, David = RAG/feedback, Abdur = dropout ML only, Yohanna = automation/CI. Do not reassign work.
- **Synthetic data only.** Flag anything that loads, logs or asks for real student data.
- **Kind tone.** Start with what is good. Explain *why*, show the fix, never blame.

## Step 1 · Gather the change

Accept any of: a PR number or URL, a branch name, or a pasted diff.

- PR: `gh pr view <n> --json title,body,author,headRefName,baseRefName,files,additions,deletions` then `gh pr diff <n>` and `gh pr checks <n>`.
- Branch: `git fetch` then `git diff origin/dev...origin/<branch>` and `git log origin/dev..origin/<branch> --oneline`.
- Pasted diff: use it as-is. Say lines may be cut off; mark anything you cannot see as "please confirm" instead of guessing.

If `gh` is not logged in, fall back to git, or ask for the diff.

## Step 2 · Read the project rules

Read the parts that apply to this change: `CONSTITUTION.md`, `AGENTS.md`, `CLAUDE.md`, `contribution.md`, `projectplan.md` (dates, guardrails). Find the Jira key (KAN-xx) in the branch, title or body. If the Jira tools are available, read that ticket's summary and acceptance criteria. Never change it.

## Step 3 · Size check

If the change is over ~400 changed lines (ignoring lockfiles and generated `schema.gen.ts`), say so first and suggest how to split it. If the diff is mostly line-ending noise (CRLF/LF), say that and stop.

## Step 4 · The five reviewers

Run each reviewer on the change. For big or risky PRs (auth, RBAC, admission decision, enrolment, CI/secrets), run each reviewer as a separate subagent that does not see the others' notes, then merge. For small PRs, do them yourself in order.

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
- New logic has tests. Permission changes have one positive and one negative test.
- Migrations: `alembic upgrade head && alembic check` would pass.
- The PR says which commands were run and their result. Missing evidence = blocked, not green.

**5. UX and accessibility** (only if `src/` changed)
- Works with the keyboard; labels on every field; visible focus; good contrast.
- Plain Spanish UI text using *tú*; errors say what to do next.
- Empty, loading and 401/403 states exist. No dead ends.
- Respects `prefers-reduced-motion`.

## Step 5 · Check before you report

For every finding, look at the actual code again and confirm it is real. Drop anything you cannot confirm, or mark it "please confirm". Merge duplicates from different reviewers. Fewer, true findings beat many guesses.

## Step 6 · Output

Use exactly this shape, in the user's language (English or Spanish):

```
**Verdict:** ✅ Approve | 🟡 Approve with small fixes | 🔴 Changes needed
**Checked:** what you read and what you ran (be specific)

**What's good:** 1–3 lines

**Must fix** (blocks merge): file:line · problem · why · fix
**Should fix** (small, worth doing now): ...
**Follow-ups** (later, suggested Jira ticket for each): ...

**Committee scores (1–5):** Product · Security · Code · Tests · UX (or n/a)
```

Then a **ready-to-paste GitHub comment**: short, friendly, starts with thanks or what is good, lists must-fix items with code snippets, ends with follow-ups. Mention people only by their real GitHub handle when the user gave it.

## Self-review mode

If the user asks to review their *own* work before opening a PR, use the same steps but write the output as a to-do list for them, and skip the GitHub comment.