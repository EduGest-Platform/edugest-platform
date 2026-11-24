# KAN-175 — Implementation / Implementación

## ES

Implementación: Yohanna. Tarea asignada a Elizabeth; único revisor solicitado: Anasfady. Deadline Jira: **23/11/2026**. Incremento del 24/11/2026.

Registra en cada voto nuevo los roles, ámbitos y permiso que autorizaron la firma en su convocatoria. El historial conserva esa evidencia aunque cambien permisos; los votos antiguos quedan con autoridad nula, sin reconstrucciones. Incluye migración 0014, contrato, cliente y diccionario actualizados.

## EN

Implementation: Yohanna. Jira assignee: Elizabeth. Sole requested reviewer: Anasfady.

Captures matching role/scope/permission authority on each new selection vote and exposes it in existing protected history. Legacy authority stays null instead of being reconstructed. Adds migration 0014 and regenerates contract, client and model dictionary.

## Validation / Validación

PASS: four offline authority regressions, Ruff, TypeScript, dictionary check and diff checks. Updated existing PostgreSQL vote-evidence assertions but did not run PostgreSQL locally.

## Limits / Límites

Increment for signer evidence only. It does not change quorum, decision permissions, ranking or automatically invalidate past votes. Coded internal reasons and separate external recommendations remain pending policy work. No DB migration executed locally. / No completa todos los criterios de KAN-175.

CI completion is not awaited, as requested. No Jira changes, merge or deployment. / No se espera al CI por petición del usuario. No se cambia Jira ni se fusiona o despliega.
