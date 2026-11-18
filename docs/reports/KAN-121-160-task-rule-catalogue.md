# KAN-121 / KAN-160 — Task and rule inventory / Catálogo de tareas y reglas

Prepared / fecha: 2026-11-17; revised / revisado: 2026-11-18. Owner / responsable: Yohanna. Reviewer / revisión: Elizabeth; David for rule traceability / trazabilidad del motor.
Deadlines in Jira / vencimientos: KAN-121 **19/11/2026**; KAN-160 **17/11/2026**.
Inspected / base: `dev` `774ef52` (merged PRs #10 and [#26](https://github.com/EduGest-Platform/edugest-platform/pull/26) / PRs fusionados).
**PROPOSED** business catalogue; offline behavior tested separately. No client acceptance, real minute values or production savings are claimed. / Catálogo de negocio propuesto, sin aprobación cliente, minutos reales ni ahorro en producción acreditados.

## 1. ES — unidad, límites y fuentes

La preselección va desde inscripción hasta convocatoria a selección, retirada expresa o resolución humana del silencio. La entrevista de selección y la decisión de admisión quedan fuera. Para el cálculo, la fórmula canónica y validaciones están en [README del evaluador](../../evals/automation/README.md): ahorro de tiempo estimado ponderado por minutos del tipo de tarea, con tareas y casos elegibles por separado. La PO confirmó esa definición el 17/11; la aprobación formal de Melissa, catálogo vigente y unidad persona/lote siguen pendientes.

Fuentes comprobadas: `api/app/modules/automation/engine.py`, `evals/automation/metrics.py`, su README y suite offline, `api/app/modules/admissions/{schemas,router}.py`. Los tiempos 20/15/20 solo se conservan como referencias orientativas comunicadas en las guías y revisión PO; no se han vuelto a consultar los documentos privados AS-IS/TO-BE ni se certifica su aprobación desde este PR.

La unidad propuesta es **una ocurrencia real de actividad por candidatura**, no una fila por aspirante para cada actividad posible. Una persona puede necesitar cero, uno o varios contactos: las frecuencias se obtienen de eventos, nunca se suponen iguales. No sumar 20+15+20 por cada candidatura. Un evento CRM `recordatorio` no es prueba de ejecución automatizada.

## 2. ES — actividades y elegibilidad propuesta

La lista técnica `PRESELECTION_TASK_TYPES` permite representaciones, **no aprueba actividades de negocio ni convierte propuestas en ahorro**. Cada fila debe validar etapa, finalidad y ejecución. Sin catálogo aprobado, no publicar una cifra del 70 %.

| ID | Actividad / tipo técnico relacionado | Denominador propuesto | Numerador posible | Estado y frecuencia |
|---|---|---|---|---|
| CAT-01 | Revisar requisitos caso a caso / `requirements` | Pendiente: separar trabajo humano no automatizable de comprobaciones mecánicas acordadas | No por la señal `human_review`: requiere valoración humana | Motor solo consume faltantes ya calculados; una revisión real/versionada por necesidad, no por cada evaluación del motor |
| CAT-02 | Pedir información inicial / sin acción propia | Pendiente de política y modelo de tarea | No implementado | No confundir la petición inicial con un seguimiento posterior; solo cuando falta información |
| CAT-03 | Seguimiento de documentación / `documentation` | Candidata, con aceptación de alcance y minutos propios | Solo ejecución completa verificada de la tarea simulada acordada, nunca mera propuesta | Una ocurrencia por tarea/versión/contenido; no atribuir automáticamente los 15 minutos de petición inicial |
| CAT-04 | Recordar jornada informativa / `information_session` | Candidata si la candidatura sigue en preselección | Solo ejecución registrada y verificable dentro del alcance de demo acordado | Una tarea concreta por jornada; ventana previa configurada; no equivale a crear convocatoria ni cita |
| CAT-05 | Recordar ejercicios preparatorios / `exercises` | Candidata si es preparación no excluyente | Solo ejecución registrada del seguimiento acordado | Tras vencimiento; no corrección automática, puntuación ni requisito excluyente |
| CAT-06 | Revisar silencio / `response` | Pendiente: revisión humana separada de la detección mecánica | No por la señal de revisión humana | Vencimiento + margen por convocatoria; jamás cierre automático |
| CAT-07 | Inscripción y ficha única / sin tipo del motor | Pendiente de decidir si entra como actividad medible | No atribuible a este motor | API F1 persiste candidatura; su existencia no mide ahorro de la regla administrativa completa |
| CAT-08 | Entrevista, puntuación humana, decisión, reserva y matrícula / `interview` o tipos externos | Excluidas de este 70 % de preselección | Nunca | Actividades humanas/de selección; no renombrarlas como tipos permitidos |

**Limitación de granularidad:** el evaluador actual asigna minutos por `task_type` técnico. No puede distinguir dos actividades con distintos tiempos que compartan el mismo tipo. Elizabeth debe acordar una correspondencia uno-a-uno para el catálogo inicial o un contrato posterior que separe actividad de negocio/tipo del motor; no inventar aliases ni cargar ambas actividades con un único tiempo por conveniencia. Por eso este inventario no se suministra como catálogo de minutos ejecutable.

## 3. ES — reglas presentes y excepciones

| Regla | Disparo comprobable en código | Excepción / control | Estado |
|---|---|---|---|
| R-01 Política por convocatoria | `enabled=True`, convocatoria coincidente | Desactivada por defecto; convocatoria ajena o tareas duplicadas se rechazan | Núcleo offline |
| R-02 Faltantes | `requirements` con tupla no vacía | Solo `human_review`; conjunto vacío no dispara; no valida el requisito ni excluye | Núcleo offline |
| R-03 Silencio | `now >= due_at + response_grace` (instantes UTC) | Campo obligatorio por convocatoria; admite cero: dispara exactamente al vencimiento, sin espera adicional. Tarea completada no dispara; resolución humana | Núcleo offline |
| R-04 Jornada informativa | `due_at - reminder_lead <= now < due_at` | Margen cero desactiva; después del inicio no propone aviso | Núcleo offline |
| R-05 Seguimiento | Documentación/ejercicios desde `due_at + reminder_delay` | Tarea completada o aún en plazo no dispara | Núcleo offline |
| R-06 Entrevista | Seguimiento simulado en selección | No elegible para métrica; también se rechazan tipos desconocidos elegibles | Núcleo offline, fuera del 70 % |
| R-07 Duplicación | Clave por convocatoria/candidatura/tarea/versión/acción/huella | Reintentos y orden de faltantes conservan clave; cambios de conjunto/versión crean nueva propuesta | Una propuesta no garantiza unicidad concurrente |
| R-08 Puntuación/excepción/admisión | No implementadas por este núcleo | Sin umbrales de exclusión; revisión y firma humanas con contrato F2 pendiente | Bloqueado para inventario definitivo por reglas F2 |

Desde la integración del [PR #26](https://github.com/EduGest-Platform/edugest-platform/pull/26), R-03, R-04 y R-05 calculan sus duraciones como **tiempo transcurrido**, normalizando `now` y `due_at` a UTC antes de operar y comparar: 24 horas son 24 horas reales incluso durante cambios de hora, no un día de calendario local. Las fórmulas de la tabla usan esos instantes; el margen cero de R-04 desactiva el recordatorio, mientras que el margen cero de R-03 permite revisar el silencio al vencimiento. La presencia de este comportamiento en código no sustituye la aceptación PO de la política ni aprueba minutos/catálogo.

La cardinalidad aceptada por David en PR #10 es un recordatorio por tarea/versión/contenido. No aumentar versiones por ejecución para eludir deduplicación. La revisión por silencio es una tarea independiente. Conservar el caso de entrevista individual sin penalización y requisitos en estudio como escenarios pendientes de F2, no inventar su algoritmo aquí.

## 4. ES — evidencia, tiempo y pendientes de aceptación

Para cada ocurrencia candidata: candidatura sintética, convocatoria y etapa al ejecutar; ID de tarea/actividad; versión de catálogo/política; resultado manual/automatizado; instante; referencia única de ejecución y auditoría mínima. Mantener fuentes/fechas de los minutos sin texto libre sensible. La autenticidad, RBAC/etapa, transacción/outbox y persistencia siguen pendientes del adaptador. Una propuesta `simulated_reminder` o `human_review` no habilita por sí sola `automated=True`.

Los minutos deben representar la misma unidad que las ocurrencias; si el tiempo es por lote, acordar unidad/asignación antes del cálculo por candidatura. Denominador cero es desconocido, no éxito. El mínimo de 100 cuenta solo candidaturas con actividad elegible. Informar valores inferiores al 70 %, supuestos y costes humanos residuales; la fórmula actual es una estimación de sustitución completa, no un cronómetro de producción.

- [ ] Elizabeth valida filas elegibles/excluidas, granularidad y reglas F2 de puntuación/excepciones.
- [ ] Melissa valida formalmente fórmula/catálogo y unidad persona/lote; minutos/frecuencias no se inventan.
- [ ] Confirmar que evidencia de ejecución simulada satisface la rúbrica de demo y cómo medir trabajo residual humano.
- [ ] Dataset KAN-79 y registros KAN-183 conectados antes de resultados del producto.
- [ ] Revisión cruzada antes de cerrar KAN-121; KAN-160 sigue parcial hasta reglas F2 e inventario definitivo.

## 5. EN — canonical meaning of this inventory

This is a proposed business inventory mapped to the merged offline engine, not an approved executable minutes catalogue. Preselection ends at selection invitation, explicit withdrawal or human resolution of silence. Selection interviews, human scoring, admission/waitlist/enrollment decisions are excluded. The canonical estimated-time-saved formula and guards remain in the evaluator README linked above; PO confirmed the definition, while formal client approval, current minutes and person/batch interpretation remain pending.

An occurrence represents an actual activity for one synthetic application, not one instance of every possible task for every applicant. Frequencies come from records; never add the indicative 20/15/20 estimates once per applicant. Technical task-type eligibility does not approve business scope or prove automation. CAT-01 requirements and CAT-06 silence still need human review; their signals do not earn estimated savings. CAT-02 initial information requests and CAT-07 registration are not implemented as motor actions. CAT-03/04/05 follow-up/reminder activities are candidates only after scope/minute approval and verifiable completion within the agreed demo scope; a CRM event or proposal alone is insufficient.

The evaluator assigns minutes per technical task type. Distinct business activities sharing a type cannot carry different timings without an approved one-to-one mapping or future contract change. Do not introduce arbitrary aliases to bypass the guard or reuse initial-request time for a follow-up. No real minute catalogue is provided by this PR.

The rules table records existing behavior: disabled-by-default call policies, missing-list human review, required call-specific silence grace, pre-session information reminders, post-deadline documentation/exercise follow-up, no action for completed tasks, selection-interview exclusion and stable version/content keys. One reminder per task/version/content was accepted for this increment by David. Changed versions/missing sets create a new proposal; concurrent uniqueness still needs database/outbox integration. No scoring/exception/admission algorithm is implemented; F2 rules need Elizabeth's definition before KAN-160 can be final.

R-03's `response_grace` is a required field but may be zero: silence is then flagged exactly at the deadline, with no additional waiting period. This differs from R-04's zero `reminder_lead`, which disables the pre-session reminder. Following merged [PR #26](https://github.com/EduGest-Platform/edugest-platform/pull/26), R-03/R-04/R-05 use elapsed durations: `now` and `due_at` are normalized to UTC before arithmetic/comparison. Twenty-four hours remain 24 real hours across daylight-saving changes, rather than one local calendar day. This documents code behavior; PO policy acceptance and business catalogue/minutes approval remain separate and pending.

Required occurrence evidence includes scoped application/stage, unique task/activity and execution reference, catalogue/policy versions, timestamp/result and minimal audit. No sensitive notes. Authentication of evidence, backend RBAC/stage checks and persistence are not delivered here. Agree batch units before applicant-level calculation, report unknown for zero denominator, require 100 eligible applications, and disclose assumptions, below-target results and residual human work. This is not production time measurement or automatic exclusion.

Elizabeth reviews scope/granularity/F2 exceptions, Melissa formally accepts formula/minutes/unit and demo evidence, and the unified dataset/execution records are integrated later. KAN-121 requires cross-review; KAN-160 remains partial until F2 rules are available. No Jira changes, migrations, new permissions or runtime behavior changes are included.
