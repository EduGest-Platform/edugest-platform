# Project Constitution — Gistar (working name) · Somos F5 Final Project 2

> **Version 1.0 · 2026-11-11 · Canonical language: English.** Spanish translation: [CONSTITUTION.es.md](CONSTITUTION.es.md). If the versions ever disagree, this file prevails.
>
> This constitution is the top of the documentation hierarchy. Operational detail lives in [AGENTS.md](AGENTS.md) (AI agents), [contribution.md](contribution.md) (human workflow), [commands.md](commands.md) (commands), [projectplan.md](projectplan.md) (roadmap) and [README.md](README.md) (entry point). Those documents refine this one; they must never contradict it.

## 0. Purpose and scope

One accessible, auditable web platform for the complete learner journey: public catalogue → application → preselection → selection with **human decision** → enrolment → cohort learning → teacher support, retrieval assistant and monitored risk indicators. It applies to every contributor, human or AI agent, working in this repository.

**Delivery gates:** development freeze **2026-12-04**, defence rehearsal **2026-12-09**, final defence **2026-12-10**.

**Team:** Yohanna (Scrum Master + automation), Elizabeth (Product Owner + backend/PostgreSQL/FastAPI), Anas (frontend), David (RAG/assistant), Abdur (dropout-prevention ML only). Do not reassign roles from older documents.

## A. Architecture and reuse

1. Keep the existing stack: **React 19 + Vite 8 + TypeScript + Tailwind CSS 4** (web, at repo root as Figma Make runs it), **FastAPI + SQLAlchemy 2 + Alembic** (`api/`), **PostgreSQL 16** as the single source of truth for operational data.
2. The API contract is **OpenAPI** (`contracts/openapi.json`); the TypeScript client is generated from it (`pnpm gen:api`). Backend and frontend never drift from the contract silently.
3. Clear separation between presentation (`src/`), domain/API (`api/app/modules/`), persistence (SQLAlchemy models + Alembic migrations) and AI components.
4. Database changes only through **versioned Alembic migrations**, reversible where possible. No schema drift, no duplicated data models.
5. No mass refactors, no framework migrations (no Astro/Next), no root restructuring, microservices or new infrastructure without an approved ADR in `docs/adr/` proving objective technical necessity and passing checks.
6. Preserve Figma Make compatibility while it is in use: `.figma/`, `vite.config.ts` plugins and the `@` alias, `.mise.toml`, Tailwind v4 via `src/index.css`.

## B. Code quality

1. **All code and identifiers in English**: variables, functions, classes, paths, endpoints, schema fields and tests. UI copy follows the product language.
2. **Code must be understandable by humans.** Clear names, small functions and modules with one responsibility, and comments only where the code cannot speak for itself. Readability wins over cleverness.
3. Static typing where the language supports it (TypeScript strict on the web, Pydantic/typed Python on the API).
4. Backend validates all inputs; errors are handled explicitly, never swallowed.
5. Tests proportional to impact: unit (Vitest, pytest), integration, and at least one E2E per critical flow; every RBAC-sensitive change includes one positive and one negative authorization test.
6. New dependencies require written justification; protect compatibility with existing functionality.

## C. Security and privacy

1. **Synthetic data only** during development and demos. Never real student data.
2. Secrets never enter the repository. Environment variables are documented with safe example files (`api/.env.example`); demo credentials are synthetic and rotated before any deployment.
3. Authorization in the backend, **deny by default**, by role + action + scope (programme/call/cohort). Hiding UI is not security; check 401/403 and horizontal access (IDOR).
4. Least privilege everywhere; relevant operations (admission signatures, access changes, attendance corrections, privileged comments) are audited.
5. Data minimization: log only what is necessary; no personal data in model prompts or logs.
6. The assistant reaches PostgreSQL **only through allowlisted read-only backend functions**. An LLM never executes arbitrary SQL, never receives a database URL or credential, and never chooses its own scope.
7. Never publish private information or credentials, in code, docs, issues or transcripts.

## D. Responsible AI

1. RAG answers come from authorized, scope-filtered documents, with source citations and **abstention** when evidence is missing; never fabricate data or zeros.
2. Document answers (RAG) and operational data queries (read-only tools) are separate paths, both through the backend.
3. Evaluate faithfulness and unsupported claims before presenting assistant features as working.
4. Dropout ML is **advisory only**: documented synthetic training data, metrics, model card and limitations. AI-drafted feedback requires teacher approval before publishing.
5. Human review for every alert and sensitive outcome. **The AI never automates admission, exclusion, expulsion, sanctions or dropout decisions about people.**
6. Record versions of models, rubrics, prompts and relevant decisions.

## E. Collaboration and Scrum

1. The Product Owner (Elizabeth) orders and accepts the Product Backlog; the team agrees Sprint Goal and Sprint Backlog; the Scrum Master (Yohanna) facilitates events and removes impediments.
2. One primary owner per story plus a different cross-reviewer; Definition of Ready and Definition of Done as defined in [contribution.md](contribution.md).
3. Acceptance criteria are measurable; frequent integration through small PRs; no direct merge to `main` without review.
4. Impediments and decisions are documented (ADRs, increment logs in `docs/`).
5. Priority goes to verifiable functional increments over demo screens without backend.
6. **No task is marked complete without evidence** (commands run, dates, results). Blocked or not-run is never "done". Status labels: `VERIFIED_RUNNING`, `CODE_PRESENT_NOT_RUN`, `MOCK`, `PROPOSED`, `BLOCKED`.

## F. Working with AI agents

Explicit guardrails for Claude, Codex and any other agent (operational detail in [AGENTS.md](AGENTS.md)):

1. Read the relevant instructions (this constitution, `AGENTS.md`, `CLAUDE.md`) before modifying code; inspect before implementing.
2. Never assume a mocked feature is implemented; never represent a mock as a working backend, AI or prediction.
3. Do not modify files outside the requested scope; no destructive migrations, no changes to secrets, real permissions or external services without authorization.
4. No commits, pushes, merges, deployments, Jira changes or account/publishing actions without explicit human approval.
5. Never invent test results; report exactly what was run and what was not.
6. Document every modified file and its justification.
7. Keep `AGENTS.md`, `CLAUDE.md` and this constitution consistent; a change to one is checked against the others.

## G. Product identity and legal

- Own product name and artwork. **Do not use the Somos F5 name or logo as the product brand**; colour inspiration only. No licensed material or proprietary screenshots.
- This repository declares **no license** until the Product Owner and Somos F5 approve one; absence of a license means all rights reserved.

## H. Documentation and language policy

- Repository documentation is **bilingual Spanish/English**: either paired sections inside one file or a canonical file plus a clearly marked translation (`NAME.md` canonical + `NAME.es.md`), cross-linked.
- One canonical source per rule; translations never introduce rules of their own.
- Code identifiers, paths, commands and API names are never translated.
- Documentation always distinguishes implemented, simulated, pending and verified functionality.
