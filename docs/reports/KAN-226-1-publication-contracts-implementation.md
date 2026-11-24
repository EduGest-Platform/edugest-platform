# KAN-226 — Implementation / Implementación

## ES

Implementación: Yohanna. Tarea asignada a Elizabeth; único revisor solicitado: Anasfady. Deadline Jira: **Sin fecha en Jira / No Jira due date**. Incremento del 24/11/2026.

Primer tramo del catálogo público, sobre KAN-224/KAN-226 de Elizabeth. Añade estado editorial y versión; las nuevas convocatorias son borradores y la migración conserva la visibilidad de las ya expuestas. Proyección pública mínima con campos actuales, sin aprobar decisiones PO pendientes.

## EN

Implementation: Yohanna. Jira assignee: Elizabeth. Sole requested reviewer: Anasfady.

Define draft/published call visibility, optimistic publication versions and a minimal public offer projection. Existing publicly exposed calls retain visibility; new calls default to draft. KAN-224 content remains a technical proposal, not PO acceptance.

## Validation / Validación

14 offline policy/schema tests passed; Ruff and diff checks passed. Upgrade/downgrade SQL rendered offline. PostgreSQL migration execution and drift check NOT RUN: local database unavailable.

## Limits / Límites

This foundational PR does not filter existing endpoints until phase 4. No UI, content editor, email or Jira changes. Downgrading removes editorial visibility and must be evaluated before rollback; no shared database migration executed.

CI completion is not awaited, as requested. No Jira changes, merge or deployment. / No se espera al CI por petición del usuario. No se cambia Jira ni se fusiona o despliega.
