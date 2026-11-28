# KAN-76 · Guion y lista de comprobación / Demo script and operator checklist

**ES** — Usar durante el ensayo humano y la presentación. El ensayo automatizado de KAN-221 y el procedimiento de respaldo de KAN-212 aportan evidencia de preparación. Registrar las comprobaciones del entorno y de la persona presentadora el día del ensayo.

**EN** — Use this checklist for the presenter rehearsal and the defence. KAN-221 provides automated rehearsal evidence and KAN-212 describes the local fallback. Record environment and presenter checks during the live rehearsal.

## Antes del turno / Before the slot

| Comprobación / Check | Resultado para salir a demo / Go criterion |
| --- | --- |
| Entorno y revisión / Environment and review | ES: Registrar entorno y SHA. Confirmar que el SHA tiene CI y E2E en verde y que la persona responsable ha revisado el entorno autorizado. EN: Record the environment and SHA, confirm CI and E2E for that SHA, and confirm the operator reviewed the authorized environment. |
| Cuentas y datos / Accounts and data | ES: Confirmar cuentas sintéticas, permisos para cada paso y sesiones disponibles en ventanas separadas. EN: Confirm synthetic accounts, access for each step and separate browser windows. |
| Respaldo local / Local fallback | ES: Arrancar y comprobar el entorno local antes del turno con la guía KAN-212. Confirmar que la API, la base, la web y los datos de la demo responden. Cargar el corpus sintético según la guía del ensayo. EN: Start and smoke-test the local stack before the slot using KAN-212. Confirm the API, database, web and demo fixtures are available, and load the synthetic corpus as described in the rehearsal guide. |
| Guion y capacidad de recuperación / Script and recovery | ES: Confirmar quién presenta, quién opera el respaldo y qué expediente continuar en cada entorno. EN: Identify the presenter and fallback operator and the dossier to use in each environment. |

## Recorrido de 15 minutos / 15-minute walkthrough

| Minutos / Minutes | Qué mostrar / What to show | Comprobación visible / On-screen evidence |
| --- | --- | --- |
| 0–4 | Abrir el catálogo público, elegir una convocatoria y completar una solicitud sintética. / Open the public catalogue, choose a call and submit a synthetic application. | Recibo y código de expediente. / Receipt and application code. |
| 4–9 | Abrir el expediente en Captación, revisar un requisito y pasar a la decisión humana. / Open the dossier as Recruitment, review a requirement and hand it off for a human decision. | Mostrar los votos autorizados y el resultado solo al alcanzar el quórum configurado. / Show authorized votes and the result when the configured quorum is met. |
| 9–12 | Acceder a la matrícula y registrar asistencia desde la cohorte docente autorizada. / Open the enrollment and record attendance from the authorized teaching cohort. | Una matrícula y el registro de asistencia visible después de actualizar. / One enrollment and the attendance record after refresh. |
| 12–15 | Consultar al asistente con una pregunta del corpus de demo. / Ask the assistant a question covered by the demo corpus. | Mostrar la cita o la abstención de la consulta. / Show the citation or the abstention returned for the question. |

## Contingencia / Contingency

**ES** — Ante un fallo de datos, permisos o servicio, pausar y verificar una vez el entorno y perfil. Si persiste, pasar al entorno local ya comprobado y anunciar el cambio. Reanudar desde el expediente sintético de respaldo e indicar qué pasos se repiten. Si el respaldo falla, mostrar la evidencia del ensayo con su fecha y SHA y marcar la ejecución en vivo como interrumpida.

**EN** — On a data, permission or service failure, pause and check the environment and role once. If it persists, announce the switch to the pre-checked local stack, resume from its synthetic dossier and identify any repeated steps. If the fallback also fails, show the dated rehearsal evidence and record the live run as interrupted.

### Escritura con resultado incierto / Write with an uncertain result

**ES** — Si se pierde la respuesta después de enviar una candidatura, votar o registrar asistencia, comprobar el expediente, la decisión o el registro al actualizar la vista en ese mismo entorno. Si aparece el resultado, continuar desde ahí. Si no se puede comprobar, anotar «resultado incierto» y seguir desde un expediente sintético distinto en el respaldo. Antes del ensayo, comprobar que la cuenta del respaldo puede abrir ese expediente y que su punto de partida es el esperado.

**EN** — If the response is lost after submitting an application, casting a vote or recording attendance, refresh the dossier, decision or attendance record in the same environment. Continue from the result if it is visible. If the result cannot be verified, record it as uncertain and continue with a different synthetic dossier in the fallback. Before the rehearsal, confirm that the fallback account can open that dossier and that it is at the expected stage.

## Acta del ensayo / Rehearsal record

| Fecha y SHA / Date and SHA | Entorno / Environment | Presentación / Presenter | Total / Duration | Resultado y evidencia / Result and evidence |
| --- | --- | --- | --- | --- |
| Pendiente / Pending | — | — | — | NOT_RUN |

**ES** — Si se usa el respaldo, registrar el tramo del guion, el último punto verificado, el entorno y SHA de respaldo y si se pudo completar el recorrido. / **EN** — If the fallback is used, record the script segment, last verified point, fallback environment and SHA, and whether the journey was completed.

- [Guion inicial / Initial script](KAN-141-preselection-demo.md)
- [Ensayo automatizado / Automated rehearsal](KAN-221-demo-rehearsal.md)
- [Respaldo local / Local fallback](../deploy/KAN-212-local-fallback.md)
- [Evidencia de recuperación de BD / Database restore evidence](KAN-217-disposable-backup-restore.md)
