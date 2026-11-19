# KAN-135 — Per-call requirements / Requisitos por convocatoria

## ES — alcance y decisiones para revisión

Base: `dev` `4a0ea58` (19/11/2026), después de #40. Se configura un catálogo de definiciones por convocatoria, con identificador opaco `ref`, código lógico, etiqueta, tipo `required`/`recommended`, financiador opcional y versión. No se añaden criterios reales, umbrales de edad, puntuación, exclusión ni decisiones de admisión. El financiador es una etiqueta de procedencia, no un rol ni una regla automática.

- `GET /api/v1/calls/{call_id}/requirements`: todos los registros/versiones del ámbito, ordenados por código y versión; exige `requirements.read` con el control existente de programa/convocatoria/cohorte.
- `POST` en la misma ruta: administración publica una definición inmutable. No se conceden permisos nuevos a otros perfiles. Es una propuesta conservadora para revisión de Elizabeth, no aceptación PO de un nuevo reparto de permisos.
- `expected_version=0` crea un código; la versión siguiente exige la versión vigente y una referencia nueva. Se serializa la publicación bloqueando la convocatoria; referencias duplicadas o versiones obsoletas devuelven 409. Cambiar etiqueta, tipo o financiador exige una versión nueva. No hay PUT/DELETE ni activación silenciosa de una versión sobre candidaturas existentes.
- `PUT` de revisión exige que la referencia exista **en la convocatoria de la candidatura**. Una referencia ajena/desconocida devuelve 404 sin escritura. La revisión y cada nueva fila de historial conservan `requirement_definition_id`; publicar otra versión no cambia sus resultados ni la etapa.
- Datos anteriores: la migración no inventa definiciones ni rellena vínculos. Un identificador de definición nulo significa revisión histórica no vinculada. Solo una revisión humana explícita, con una referencia configurada y la versión de concurrencia correcta, añade el vínculo; las filas de historial anteriores siguen sin vincular. No presentar esas filas como requisitos oficialmente validados.
- La base bloquea UPDATE/DELETE ordinarios de definiciones; no se afirma protección frente a administradores/DDL/TRUNCATE. La auditoría guarda ID/versión, sin etiquetas, financiadores ni motivos libres.

La migración `0006` cuelga de `0004`, la cabeza integrada al preparar el PR. #46 sigue abierto con `0005`: quien integre después debe reconciliar la cadena para conservar una sola cabeza; no aplicar migraciones en una BD compartida para resolverlo. El catálogo no implementa publicación de un conjunto completo por candidatura, activación, retiro de definiciones, herencia automática por financiador ni UI. Esos cambios necesitan contrato y revisión adicionales; aquí cada revisión selecciona una referencia inmutable explícita.

## EN — scope and review decisions

Based on `dev` `4a0ea58` (19/11/2026), after #40. Adds a per-call definition catalogue with opaque reference, logical code, label, required/recommended kind, optional funder provenance and version. It introduces no real criteria, age thresholds, scores or automatic admission/exclusion decisions. Funder is provenance metadata, not an authorization role or executable condition.

Scoped readers use the existing `requirements.read` permission. Only the existing admin wildcard can publish definitions: this conservative permission proposal requires Elizabeth's review, not implied PO acceptance. First publication uses expected version zero; successors require the current version and a fresh reference. Call-row locking serializes publication; stale versions or reused references return 409. Definitions are immutable; changes require a new version. Listing returns all versions, without silently selecting a new version for an existing applicant.

Review writes resolve the reference inside the application's call or return 404 without writes. Current reviews and new history rows retain the exact definition ID, unaffected by later publications; application stage stays unchanged. Legacy rows remain null/unverified. Only explicit human re-review with a configured reference and correct concurrency version binds the current review; old history stays unverified. No historical definition is invented or silently backfilled. Ordinary database UPDATE/DELETE is blocked, not administrator/DDL/TRUNCATE access. Audit metadata contains IDs/versions only.

Migration `0006` follows integrated `0004`; pending #46 uses `0005`. Reconcile the chain when the second PR integrates, preserving one head without rewriting applied migrations. No shared database operations. Whole-catalogue activation per applicant, retirement, automatic funder inheritance and UI are outside this increment and require a follow-up contract.

## Validation / Validación

Focused tests cover publication/read, permissions, per-call isolation, new versions preserving old reviews, duplicate/stale rejection, invalid/spoofed fields, database immutability and compatibility with the existing review suite. Existing tests explicitly configure synthetic requirements as fixtures; the product seed does not invent a business catalogue.

Local validation and actual CI outcomes are recorded in the PR. Docker/PostgreSQL unavailable locally is NOT RUN, never a pass. OpenAPI and the generated client change together. No Jira changes, deployment or automatic task completion. Reviewers: Elizabeth (primary: policy/data), David (secondary: review integration/version history).
