# KAN-49 — Documentary accreditation / Acreditación documental

## ES

[KAN-49](https://anasfady87-1789923749606.atlassian.net/browse/KAN-49), asignada a Elizabeth; implementación Yohanna y revisor solicitado Anasfady. Ventana propuesta hasta el 27/11; la historia no tiene `duedate`. Esta ampliación cubre el criterio documental pendiente, sin duplicar la transición de admisión/matrícula ya integrada. No implica Jira Done ni aceptación PO.

### Integración y datos

Orden del stack: modelo/contrato → consulta → acreditación → retirada/historial → seguridad. La primera base es `dev`; las siguientes dependen de la anterior. Migración `0019` después de `0018`.

`Enrollment` conserva persona, cohorte, candidatura y ciclo académico. Se añaden `documentation_state` (`pending`/`accredited`), `documentation_version` (>= 1) y persona/fecha de acreditación. Una restricción exige ambos datos al acreditar y ambos nulos cuando está pendiente. Toda matrícula existente o nueva empieza pendiente: no se deduce verificación documental de una admisión o del seed. No hay archivos, URLs, nombres de documentos ni notas libres.

`pending` significa que no consta una acreditación vigente; no afirma que alguien ya revisó la documentación. En matrículas históricas sin decisión de admisión enlazada, la acreditación se rechaza hasta contar con trazabilidad verificable; este stack no fabrica ni migra decisiones históricas.

### Contrato y permisos

Rutas bajo `/api/v1/enrollments/{enrollment_id}/documentation`:

| Método / Ruta | Comportamiento |
|---|---|
| `GET` | Estado, versión y fecha; lectura propia o ámbito existente de `applications.read` |
| `POST /accredit` | Administración global registra una acreditación humana explícita |
| `POST /revoke` | Administración global retira la acreditación; no da de baja la matrícula |
| `GET /history` | Historial paginado, máximo 100: versión, estado y fecha, sin identidades del verificador |

Los POST aceptan solo `expected_version`, entero estricto >= 1. Identidad y fecha las fija el servidor. Permisos de escritura: únicamente la administración global ya existente; no se otorgan roles nuevos a captación, selección o docentes. La autorización de lectura propia no permite acreditar. Una persona que solicita otra matrícula recibe `404`; personal de otro ámbito recibe `403`. Todos los endpoints exigen sesión y respuestas sin caché.

Para acreditar: matrícula activa, misma persona y candidatura admitida, cohorte de la misma convocatoria y `SelectionDecision` admitida enlazada a esa matrícula. La candidatura se bloquea antes de la matrícula; después se comprueba la versión bajo bloqueo. Cada cambio real incrementa versión y registra auditoría en la misma transacción. Repetir el mismo estado con versión vigente no crea otro evento; una versión antigua responde `409`.

La retirada puede corregir evidencia incluso después de una baja académica. Vuelve a `pending`, limpia persona/fecha actuales y conserva los eventos históricos append-only. Una nueva acreditación exige de nuevo todas las condiciones. El historial excluye eventos de consulta y proyecta solo los cambios documentales; vacío no equivale a verificación histórica.

### Límites y privacidad

La acreditación es un registro administrativo humano, no una comprobación automática de documentos ni una garantía jurídica. No cambia la decisión de admisión, el estado académico, `RoleAssignment`, el acceso docente/coder o los permisos del asistente. El gating académico por documentación y los permisos de verificación para otros roles necesitan definición PO adicional y quedan fuera. No hay UI ni subida de documentación.

Persona verificadora y fecha son metadatos operativos relacionados con una matrícula: el identificador del personal queda en persistencia/auditoría, no en la proyección que ve el alumno. No se incorporan nuevos campos personales de candidatura ni categorías sensibles. Retención y cualquier uso con documentos reales requieren decisión humana; solo se usan fixtures sintéticos.

La migración inversa elimina el estado documental actual; exige respaldo de evidencia antes de aplicarla. No se ejecutó contra ninguna base compartida. El historial auditado no se reescribe al retirar una acreditación.

### Verificación

Pruebas offline de permisos, entradas, coherencia de admisión, anonimato y contrato. Casos PostgreSQL de lectura propia/ámbito, acreditación única, ciclo retirar/reacreditar, historial, restricciones, fallo de auditoría tras `flush` y escrituras concurrentes. Se recopilaron, pero no se ejecutaron localmente; no hay evidencia local de transacciones, concurrencia real, migración aplicada o E2E sobre PostgreSQL. El SQL de upgrade/downgrade se generó offline. CI y revisión humana deben verificar esos límites antes de fusionar; no se espera al CI por petición del usuario.

Evidencia del 24/11/2026: 33 pruebas offline API/contrato PASS; 117 pruebas web PASS; Ruff, TypeScript, build y `git diff --check` PASS. Las 15 pruebas PostgreSQL se recopilaron correctamente, sin ejecutarlas. Contrato OpenAPI y cliente regenerados; igualdad del contrato comprobada. La migración no se aplicó localmente.

## EN

KAN-49 belongs to Elizabeth; implementation Yohanna; sole requested reviewer Anasfady. The proposed window ends 27 November but the story has no due date. This stack addresses the remaining documentary criterion, not the already integrated admission/enrollment transition. No Jira completion or PO acceptance is claimed.

Merge in order: model/contracts, reads, accreditation, withdrawal/history, security. Migration 0019 adds pending/accredited state, version and accrediting actor/time to Enrollment. Database constraints require complete evidence only for accredited rows. Existing and new rows default to pending; legacy admission does not imply document verification. Pending means no current accreditation evidence, not a completed review. Legacy rows without linked final admission cannot be accredited by inventing provenance.

GET status/history allow the owner or existing scoped admissions readers. The response omits verifier identities and arbitrary audit metadata. All routes require authentication and no-store responses. Only existing global administration can accredit/revoke; no new role grants are introduced. POST bodies accept only a strict positive expected version; the server sets actor/time.

Accreditation requires an active enrollment, coherent admitted application/person/cohort/call and linked final AdmissionDecision (`SelectionDecision`). Locks follow application then enrollment, with version checking under lock. State changes increment version and append audit in the same transaction. Current-state repeats at the current version are no-ops; stale versions conflict. Revocation is allowed to correct evidence even after academic withdrawal, clears current accreditation evidence and preserves immutable history. Reaccreditation checks eligibility again.

This is a human administrative record, not automatic document verification or legal certification. It does not change admission, academic lifecycle, roles, teacher/coder access or assistant permissions. Academic gating, additional verifier roles, UI, uploads, file metadata and free text are outside scope. Verifier/time are operational personal metadata retained in protected persistence/audit, not learner-facing identity fields. Only synthetic fixtures are used; real-document processing and retention need separate human decisions.

Downgrade discards current accreditation metadata and requires preserving evidence first. No shared database migration was run. Offline tests and generated migration SQL are provided. PostgreSQL tests cover scope, lifecycle, rollback, constraints and concurrent writes; they were collected, not executed locally. Actual transactions, migrations/drift and PostgreSQL E2E remain unverified locally. CI completion is not awaited as requested.

Evidence on 24 November 2026: 33 offline API/contract tests and 117 web tests passed, along with Ruff, TypeScript, build and diff checks. All 15 PostgreSQL cases collected successfully but were not executed. OpenAPI/client were regenerated and contract equality passed. No local migration execution is claimed.
