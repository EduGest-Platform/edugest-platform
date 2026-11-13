# projectplan.md — Product & delivery plan / Plan de producto y entrega (V3)

**Version / Versión:** 11/11/2026 · **Product Owner / PO:** Elizabeth · **Scrum Master / SM:** Yohanna · **Development freeze:** 04/12/2026 · **Rehearsal:** 09/12/2026 · **Defence:** 10/12/2026.

## 1. Product goal / Objetivo

**ES:** Plataforma única trazable para inscripción, preselección, selección con decisión humana, matrícula y seguimiento académico, con asistente RAG/consulta segura, modelo de abandono y feedback asistido. Datos exclusivamente sintéticos.
**EN:** One auditable platform for admissions, enrolment and learning progress, with role-scoped data, human admission decisions, bounded RAG, explainable dropout ML and supervised feedback; synthetic data only.

## 2. Confirmed team / Equipo confirmado

| Person | Role / Rol | Main delivery focus / Ámbito |
|---|---|---|
| Yohanna | Scrum Master + Developer (automatización) | Automatización, recordatorios, evidencias 70%, Scrum facilitation |
| David | Developer (RAG, asistente y feedback asistido acotado) | RAG/document assistant, restricted operational queries |
| Abdur | Developer (solo ML, prevención de abandono) | Only dropout prevention ML (dataset, baseline, model card) |
| Anas | Developer (frontend) | React/Vite frontend, UI workflows, dashboards |
| Elizabeth | Product Owner + Developer (API, PostgreSQL y contratos) | PO and FastAPI/PostgreSQL/DB contracts |

## 3. Technical state / Situación técnica (Codex 10/11)

- React 19, Vite 8, TS/Tailwind present. Maintain current structure and reuse views; no Astro migration.
- FastAPI, SQLAlchemy, Alembic, PostgreSQL schema and OpenAPI present in code; backend execution **not independently verified**.
- Admission decision→Enrollment missing; academic UI still localStorage, RAG mock, dropout model not yet operational.
- Vitest blocked by EPERM; DB pytest/E2E and deployment require execution evidence.

## 4. Delivery slices / Incrementos y gates

| Iteration | Window | Core outcome | Gate |
|---|---|---|---|
| S0 · foundations | 11–13 Nov | Docker/DB/API test, Git provenance, Vitest, contract | 13/11 |
| S1 · admissions base | 16–20 Nov | public registration, single dossier, CRM/automation, RBAC | 20/11 |
| S2 · decision → learning | 23–27 Nov | human decision, enrollment, cohort/attendance; RAG/ML running parallel | 27/11 |
| S3 · integration / delivery | 30 Nov–04 Dec | testable RAG + data tool, risk baseline, evaluated 70%, ethical checks, E2E, release & manuals | 04/12 |
| Rehearsal only | 09 Dec | practiced demo, no additional feature work | 09/12 |
| Defence | 10 Dec | final presentation | 10/12 |

**ES:** El plazo final del 04/12 es fijo. Los subplazos de historias son **propuestas**. Si no se logra una puerta, el PO ajusta el alcance tras revisar la capacidad con el equipo.
**EN:** The final development cutoff is 04 Dec. Per-story dates are proposals, not validated commitments; reduce scope based on real team capacity and gate results.

## 5. Epics and technical ownership / Épicas y responsabilidad

| Epic | Goal / objetivo | Leads / responsables |
|---|---|---|
| PLAT | DB/API/auth/RBAC, staff invitations | Elizabeth (API), Anas (UI), Yohanna (workflow) |
| WEB | landing, catalogue, sign-up | Anas (UI), Elizabeth (schema/contract) |
| ADM | CRM, preselection, human decision, comments | Elizabeth (business/API), Yohanna (automation), Anas (UI) |
| EDU | cohorts, attendance 0.5/1, submissions, competency versions | Elizabeth (DB/API), Anas (UI), Yohanna (workflow/tests) |
| AST | bounded RAG and authorised attendance query | David (RAG/tools), Elizabeth (read-only API), Anas (chat UI) |
| AI | dropout baseline, alerts, feedback | Abdur (ML only), Elizabeth (alert API), Anas (alert UI), David (feedback) |
| MET | 70% task coverage, dashboards, ethics | Yohanna (measurement), Anas (dashboard), Elizabeth (ethics/PO) |
| REL | CI/E2E, privacy, docs, demo, deployment | Yohanna (SM/CI), Elizabeth (API/security), Anas (UI), David (RAG), Abdur (ML) |

## 6. Cross-cutting guardrails / Guardarraíles

- All code, symbols, schemas and tests in English; README/user instructions in Spanish and English for GitHub.
- No use of Somos F5 logo, name as product brand, protected texts or photographs. Original product identity, color palette may be inspiration.
- RBAC and scope checked server-side; coordinator can read in-scope dossiers throughout life cycle; approval by authorised human staff roles; avoid automatic rejection.
- Half-day attendance is 0.5 (morning or afternoon); full-day is 1; preserve justified/unjustified distinctions.
- Invitations to staff create staff record and separate privileged access approval; no invitation privileges granted to coders/aspirants/alumni.
- Candidate dossier/general board comments include replies and audit; no promise of live co-editing Google Docs-style without evidence.
- RAG retrieves authorised documents with citations/abstentions; operational questions use allowlisted backend tools, read-only and scope filtered; never arbitrary model-generated SQL.
- 70% first measured as eligible automatable task types; time saved is alternate metric. Show numerator, denominator, evidence and limitations.
- Retain current folder layout: `src/`, `api/`, `contracts/`, `e2e/`, `infra/`, `.github/`, `.figma/`; restructure only with ADR and passing tests.

## 7. Backlog source / Fuente del backlog

**ES:** El backlog completo de 45 historias y 175 subtareas, cronograma nominal y capacidad sin confirmar se conservan en **Mi unidad privada** del PO para revisión previa a Jira. `projectplan.md` es un resumen de coordinación, no sustituye los tickets.
**EN:** The full detailed schedule and task index remain in the PO private Drive for review; this file provides shared high-level guidance, not Jira issue ownership commitments.

## 8. Risk and decision gates / Riesgos y gates

- PO and SM review actual weekly capacity before setting Jira due dates. Never treat story points as hours.
- If DB/API does not run on 13 Nov, prioritise platform tests and stop new integrations.
- If admission/enrolment is not operational by 27 Nov, freeze secondary UI features.
- All five briefing objectives remain visible, but narrower demos must be clearly labelled and validated; no false claims about 70%, ML or RAG.
- 04 Dec code freeze; 09 Dec rehearsal; 10 Dec defence. No deployments/accounts or Jira edits without separate authorisation.
