# KAN-224 / KAN-226 — Public catalogue / Catálogo público

## ES

Implementación: Yohanna. Tareas fuente de Elizabeth; revisor solicitado: Anasfady. Estado: **CODE_PRESENT_NOT_RUN** para PostgreSQL. No implica aceptación PO, cierre de Jira ni despliegue.

Este stack reutiliza `Call` y `Program`, sin crear un catálogo paralelo. Cada oferta pública corresponde a una convocatoria. La definición editorial adicional de KAN-224 y los campos de registro de KAN-231 siguen pendientes de validación humana.

### Integración

Orden: modelo/contratos → control administrativo → consulta pública → aislamiento de inscripción → seguridad. La primera base es `dev`; cada rama siguiente apunta a la anterior. Los tramos intermedios no completan el aislamiento de borradores: integrar el stack completo antes de presentar esa funcionalidad como terminada.

La migración `0018` añade `publication_state` y `publication_version`. Las convocatorias ya expuestas por `/calls` conservan su visibilidad mediante una actualización explícita; las nuevas quedan en `draft`. El seed declara publicadas solo sus ofertas sintéticas actuales. No se ejecutó ninguna migración contra una base compartida.

### Comportamiento

- Publicación (`draft`/`published`) y admisión (`abierta`/`cerrada`) son estados independientes. Una oferta publicada cerrada se puede consultar, pero no admite inscripciones.
- Solo la administración global existente consulta la cola y publica/retira ofertas. No se conceden permisos nuevos a captación, docentes o administración limitada a programa.
- `GET /api/v1/catalog/publications` admite filtro de estado y paginación hasta 100. `GET /api/v1/calls/{call_id}/publication` devuelve estado y versión; `PUT` exige `state` y `expected_version`.
- Cada cambio real bloquea la convocatoria, verifica versión, incrementa versión y escribe auditoría en la misma transacción. Repetir el estado actual con versión vigente no genera otra revisión. Versión obsoleta: `409`. Nombre vacío, fechas invertidas o plazas negativas impiden publicar (`422`).
- `GET /api/v1/public/courses` devuelve `items` y `total`, con filtros `program_id` y `admission_state`, `limit` de 1–100 y `offset` no negativo. El orden es fecha de apertura descendente e identificador como desempate. El total incluye solo ofertas publicadas que cumplan los filtros.
- `GET /api/v1/public/courses/{course_id}` no distingue borrador de identificador inexistente (`404`, `public_course_not_found`). Iniciar sesión como administración tampoco revela borradores por esta ruta.
- Proyección pública: identificadores de oferta/programa, nombres, fechas de solicitud, plazas y estado de admisión. No incluye personas, descripciones libres del programa, contadores, reglas internas, versiones editoriales ni políticas de selección.
- El listado anterior `/api/v1/calls` conserva su formato, pero también excluye borradores. Inscribirse directamente en un borrador responde el mismo `404` antes de crear persona, candidatura o consumir numeración. La inscripción usa el mismo bloqueo de convocatoria que la publicación.
- Retirar una oferta no elimina candidaturas ni revoca la consulta interna autorizada. No cambia la política existente de fechas o decisiones de admisión. Los nombres son texto: las futuras vistas deben escaparlos y no usar HTML sin sanitizar.

### Validación y límites

Pruebas locales de contratos, autorización y HTTP sin base real; las dobles de base no prueban semántica PostgreSQL. Se aportan casos PostgreSQL de publicación, aislamiento, inscripción, auditoría, restricciones y concurrencia; se recopilaron, pero no se ejecutaron localmente. El SQL de upgrade/downgrade se generó offline; falta ejecutar migraciones y `alembic check` sobre una base desechable. No se espera al CI por petición del usuario.

Antes de fusionar: revisar especialmente migración de visibilidad existente, semántica editorial con la PO, suite PostgreSQL y contrato para Anas. No incluye editor de contenidos, creación de convocatorias, UI, correo o aprobación de datos pendientes. Un downgrade elimina el estado editorial y vuelve al código anterior sin filtro: no es una retirada segura de ofertas; requiere evaluación humana y respaldo de esos estados.

## EN

Implemented by Yohanna for Elizabeth's KAN-224/KAN-226, with Anasfady as requested reviewer. PostgreSQL status is **CODE_PRESENT_NOT_RUN**. No Jira completion, PO acceptance or deployment is claimed.

The stack reuses Call/Program: contracts/model, administrative lifecycle, public reads, legacy/registration isolation, security. Merge in that order and integrate the complete stack before claiming draft isolation. Migration 0018 preserves visibility of calls already exposed by the old public endpoint; future rows default to draft. Only existing synthetic seed offers are explicitly published.

Publication is independent of open/closed admission state. Existing global administrators alone can manage it. Reads expose state/version; mutations require an expected version, lock the call, increment on change and audit in the same transaction. Stale writes return 409; blank names, reversed dates and negative capacity block publication with 422. Repeating the current state at the current version is a no-op.

Public list/detail expose offer/program IDs, names, application dates, capacity and admission state only. Listing supports bounded pagination (maximum 100), program/admission filters and deterministic date/ID ordering. Counts exclude drafts. Public detail returns the same 404/code for unknown and draft IDs, even for logged-in administrators. No people, free-form program descriptions, counters, editorial versions or internal policies are projected.

Legacy `/calls` also excludes drafts. Direct registration rejects drafts before person/application writes and shares the call lock with withdrawal. Withdrawing preserves existing application history and authorized internal access. Closed published offers remain readable but cannot accept applications. Existing date-window policy is unchanged. UI consumers must render names as escaped text.

Offline checks do not substitute for PostgreSQL. Database regressions cover state changes, scopes, invalidation, registration, audit rollback, constraints and concurrent versions; they were collected, not executed locally. Migration SQL was rendered offline; upgrade/downgrade and drift still require a disposable PostgreSQL database. CI completion is not awaited as requested.

PO review of editorial scope, existing-call migration semantics and pending KAN-224/KAN-231 fields is still required. No UI, content editor, call creation or email is added. Downgrade removes editorial visibility; old code would expose calls without filtering, so rollback requires human assessment and a backup of publication state.
