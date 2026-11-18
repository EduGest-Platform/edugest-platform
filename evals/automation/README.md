# Offline automation and estimated time saved / Automatización y ahorro estimado

KAN-53 / KAN-69; owner Yohanna; review Elizabeth (metric/contract), David (rules).

```sh
python -m unittest discover -s evals/automation -v
```

## Elapsed durations and DST / Duraciones y cambio de hora

ES: `response_grace`, `reminder_delay` y `reminder_lead` representan tiempo transcurrido: un día en `timedelta` son 24 horas, no «la misma hora local mañana». El motor convierte `now` y `due_at` a UTC antes de aritmética/comparaciones, respetando los instantes de la hora repetida (`fold`). Conserva la zona original en `Proposal.proposed_at` y no cambia claves. El adaptador debe resolver la hora local ambigua/inexistente al crear la cita; aquí se esperan instantes conscientes de zona, no una nueva política de calendario civil.

EN: policy durations are elapsed time; a timedelta day is 24 hours, not the same local time tomorrow. Normalize now/due to UTC before arithmetic/comparison, including repeated-hour folds. Proposal timestamps retain their input zone and keys are unchanged. The adapter must resolve ambiguous/nonexistent local appointment times; this fix does not introduce calendar-day scheduling.

The regression suite uses `zoneinfo.ZoneInfo("Europe/Madrid")` and needs IANA data. Linux CI uses its system timezone database; Windows can install the API's `[dev]` extra, which now includes the test-only `tzdata` fallback. No runtime dependency is added. / La suite requiere datos IANA; Linux usa los del sistema y `[dev]` incorpora `tzdata` para pruebas Windows, sin dependencia nueva de ejecución.

## ES — métrica y evidencia

La PO Elizabeth confirmó el **ahorro de tiempo** como definición del 70 % en la revisión del PR #10 del 17/11/2026. La aprobación formal de Melissa, el catálogo vigente y si cada tiempo corresponde a persona o lote siguen pendientes. No hay un catálogo por defecto.

`evaluate(rows, manual_minutes={...}, catalogue_version="...")` calcula:

`porcentaje = 100 × Σ(minutos manuales del tipo de cada ocurrencia automatizada) / Σ(minutos manuales del tipo de cada ocurrencia elegible)`.

Devuelve tiempo manual base, tiempo ahorrado estimado, número de tareas elegibles/automatizadas, casos observados y casos con alguna tarea elegible. El mínimo de 100 usa **solo casos elegibles**. Denominador temporal cero produce `None`. Cada ocurrencia necesita `task_type` y cada tipo elegible necesita minutos explícitos finitos y no negativos. Identificadores se recortan antes de contar/deduplicar; flags solo aceptan bool; referencias de ejecución automatizada deben ser únicas. Su autenticidad requiere verificación independiente.

La lista explícita de tipos elegibles usa los valores de `TaskKind`: `information_session`, `exercises`, `documentation`, `requirements`, `response`. Todo otro tipo elegible se rechaza, incluyendo `interview`, `selection_interview` y tipos desconocidos, aunque tengan minutos en el catálogo. Agregar minutos nunca autoriza un tipo nuevo. El llamador debe usar un catálogo aprobado de tareas de preselección y no renombrar actividades excluidas para contarlas. Los tiempos de pruebas (5/60) son ficticios. Los 20/15/20 del TO-BE y los 30/45–60 del AS-IS v0.1 no se mezclan ni se asignan por defecto. La fórmula estima ahorro bajo el supuesto de sustitución completa de una ocurrencia: una propuesta o revisión humana no es una ejecución automatizada ni ahorro demostrado. No representa tiempos observados en producción ni costes residuales del sistema. Tiempos por lote necesitan unidad/lote acordados antes de usar el evaluador por candidatura.

## ES — alcance del motor

| Actividad | Implementado offline | Sigue humano o pendiente |
|---|---|---|
| Revisar requisitos (20 min orientativos) | Señal de revisión sobre `missing_requirements` ya calculado | Revisión caso a caso; no valida requisitos ni filtra/excluye |
| Pedir información (15 min orientativos) | Seguimiento simulado de una tarea de documentación vencida | No crea petición inicial, detecta documentos ni envía correo |
| Convocar/recordar (20 min orientativos) | Propuesta de recordatorio simulado para tareas existentes | No crea convocatoria ni cita; persistencia y bandeja pendientes |
| Silencio | Propone revisión tras `due_at + response_grace` | Una persona resuelve; no hay cierre automático |

`response_grace` es obligatorio por convocatoria, sin siete días por defecto. Políticas desactivadas de inicio. Para jornada informativa, `reminder_lead` explícito abre la ventana `[due_at - reminder_lead, due_at)`; cero desactiva el aviso previo. Para documentación/ejercicios, `reminder_delay >= 0` activa seguimiento en/después del vencimiento. No se propone un aviso de jornada ya empezada. Entrevistas pueden generar recordatorios simulados para selección pero quedan fuera del 70 % de preselección.

`completed` requiere bool; faltantes son una tupla de identificadores normalizados y ordenados. Claves de operación incluyen convocatoria, candidatura, tarea, versión, acción y huella del tipo/faltantes: cambiar el conjunto de faltantes o la versión genera una propuesta distinta; reintentos y cambios de orden no. Se revisa el conjunto actualizado completo; no se pretende enviar solo el delta. No se expone la lista en la clave. Las claves estables por sí solas no garantizan idempotencia concurrente.

Antes de integrar: autorización backend por rol/convocatoria/etapa actual, exclusión de expedientes fuera de preselección para su métrica, auditoría, PostgreSQL con restricción única + transacción/outbox, scheduler/bandeja y pruebas de permisos/concurrencia/E2E. No hay endpoints, correo real ni persistencia aquí. Las pruebas con 100 casos validan aritmética, no el dataset unificado ni el resultado del producto. CI ejecuta esta suite en un job `automation` separado sin dependencias nuevas; `sys.path` adapta el monorepo para esta prueba offline, no sustituye las pruebas API/PostgreSQL.

## EN — metric and evidence

PO Elizabeth confirmed **time saved** as the 70% definition in the 2026-11-17 PR #10 review. Melissa's formal approval, the current minute catalogue and whether minutes apply per person or batch remain pending. There is no default catalogue.

The formula above weights each eligible/automated occurrence by its task-type manual minutes. Output includes baseline/estimated saved minutes, task counts, observed and eligible case counts; only eligible cases satisfy the 100-case minimum. Zero time denominator returns `None`. Minutes must be explicit, finite and nonnegative. Identifiers are trimmed; flags must be booleans; automated occurrences need unique execution evidence. Evidence authenticity is checked independently.

Eligible types are explicitly restricted to engine TaskKind values: information_session, exercises, documentation, requirements and response. All other eligible types, including interview/selection_interview and unknown aliases, are rejected even if minutes are supplied. Catalogue membership cannot grant eligibility; callers must enforce an approved preselection catalogue without relabelling excluded activities. Test minutes (5/60) are fictitious. Do not mix AS-IS v0.1 and TO-BE estimates or sum them once per applicant. This is estimated time saved under full-replacement assumptions, not measured production savings or residual-cost measurement. A proposal/human review is not evidence of automated completion. Batch timings require an agreed unit/allocation before use with applicant occurrences.

## EN — engine and integration

Requirements only flag an already computed missing list for case-by-case human review. Documentation tasks only produce simulated follow-up; no initial information request or document validation. Existing tasks may produce simulated reminders, never invitations or actual mail. Silence becomes human review, never automatic closure. None of these proposals alone proves the indicative 20/15/20-minute tasks have been automated.

The call-specific response grace is required, without a default. Information sessions use a configurable nonnegative `reminder_lead`: `[due_at - reminder_lead, due_at)`, with zero disabling advance reminders. Documentation/exercises use nonnegative `reminder_delay` after their deadline. No information-session reminder is proposed once the session starts. Interviews remain selection activities excluded from the metric. Completed flags and missing-requirement tuples are validated. Typed actions/reasons and a fingerprint of normalized task kind/requirements distinguish changed inputs; retries/reordering retain keys. New policy versions permit new proposals. Requirement changes propose review of the whole current set, not only a delta.

Still required: adapter role/call/current-stage authorization, scoped inventory, execution audit, PostgreSQL unique constraints and transaction/outbox, scheduler/inbox, permission/concurrency/E2E tests. No endpoints, real email or persistence here. The 100 cases are arithmetic fixtures. CI now runs the offline suite in its own dependency-free `automation` job; its monorepo path setup does not replace API/PostgreSQL testing.


## Reminder cardinality / Número de recordatorios

ES: Se propone intencionadamente un solo recordatorio por tarea, versión de política y contenido normalizado. Las evaluaciones repetidas conservan la clave; el adaptador debe deduplicarla con restricción única/outbox. No hay secuencia automática de segundos avisos en este incremento. Una nueva necesidad de negocio usa una nueva tarea identificada o una política versionada tras revisión; no incrementar versión en cada ejecución para eludir la deduplicación. La revisión por silencio es una tarea RESPONSE separada con su plazo configurado.

EN: Intentionally one reminder per task, policy version and normalized content. Repeated evaluations retain the same key; the adapter must enforce unique keys/outbox. This increment has no automatic repeat-reminder sequence. A separate business occurrence needs a distinct task or an explicitly reviewed policy revision; never bump the version on each run to bypass deduplication. Silence review is a separate RESPONSE task with its configured grace period.


ES: Un tipo externo fuera de alcance puede aparecer como no elegible para observar el total, pero nunca aporta tareas, minutos o casos elegibles. Esta lista técnica no equivale a aprobación de Melissa ni valida la clasificación semántica de cada evento: el adaptador debe comprobar origen y etapa. EN: Out-of-scope types can be observed as ineligible, never counted toward eligible tasks/minutes/cases. The technical allow-list does not imply client approval or authenticate event classification; the adapter must check origin/stage.
