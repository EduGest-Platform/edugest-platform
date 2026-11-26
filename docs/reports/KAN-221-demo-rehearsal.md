# KAN-221 — Ensayo de demo / Demo rehearsal

**ES** — El ensayo automatizado usa un entorno desechable en modo API. Recorre el registro, la preselección humana, la matrícula, la asistencia y una consulta documental. Simula indisponibilidad y respuestas denegadas dentro del recorrido. El límite de 15 minutos mide las comprobaciones a partir del arranque de los servicios.

**EN** — The automated rehearsal uses disposable API-mode services. It exercises registration, human preselection, enrollment, attendance and a documentary answer. It rehearses service interruptions and denied operations. The 15-minute timer starts after service preparation.

| Minutos / Minutes | Recorrido / Walkthrough | Fallo previsto y recuperación / Expected failure and recovery |
| --- | --- | --- |
| 0–4 | Registro y expediente / Registration and dossier | La lista de convocatorias falla y vuelve al reintentar / Call list fails and loads after retry |
| 4–9 | Captación, deliberación y matrícula / Recruitment, deliberation and enrollment | Se deniega una acción ajena y un voto repetido. Solo se aplica la decisión con dos firmas distintas / An out-of-scope action and a duplicate vote are denied. The decision is applied only after two distinct approvals |
| 9–12 | Asistencia y repetición / Attendance and replay | Captación no modifica la asistencia. Repetir conserva una matrícula y una revisión / Recruitment cannot change attendance. Replay preserves one enrollment and one attendance revision |
| 12–15 | Asistente accesible / Accessible assistant | La consulta devuelve cita. Si se corta o se cancela, conserva el borrador y el foco / The answer has a citation. Failure and cancellation preserve the draft and focus |

## Reproducir / Reproduce

**ES** — Arranca PostgreSQL, FastAPI y la web en modo API sobre una base nueva con datos sintéticos. Prepara la cohorte F2 y carga el corpus sintético con embeddings desactivados. Usa el secreto demo temporal del entorno.

**EN** — Start PostgreSQL, FastAPI and the API-mode web on a fresh synthetic database. Prepare the F2 cohort and ingest the synthetic corpus with embeddings disabled. Use the environment's temporary demo password.

```sh
GISTAR_E2E_FIXTURE=disposable-synthetic WEB_URL=http://localhost:8443/ \
  GISTAR_API=http://localhost:8000/ node e2e/demo-rehearsal.mjs
```

- [Guía de entorno local / Local setup](../deploy/local-installation.md)
- [Preparación F2 y verificación de base / F2 and database verification](../../e2e/F2-admission-enrollment.md)
- [Carga del corpus / Corpus ingest](../../api/app/modules/knowledge/ingest.py)

## Evidencia / Evidence

**2026-11-26, `dev@8761001`.** Chromium, FastAPI and disposable PostgreSQL 16. El ensayo automatizado pasó en **23 segundos**, con **67** comprobaciones de registro, dos recorridos HTTP de matrícula y asistencia, y **10** comprobaciones del asistente. La verificación SQL posterior confirmó una sola matrícula y un solo registro de asistencia. Queda pendiente el ensayo humano de la presentación.

The automated rehearsal passed in **23 seconds**, with **67** registration checks, two HTTP enrollment and attendance journeys, and **10** assistant checks. Follow-up database verification confirmed one enrollment and one attendance record. The live presenter rehearsal is pending.
