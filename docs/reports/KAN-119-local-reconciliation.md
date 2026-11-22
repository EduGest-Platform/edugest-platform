# State reconciliation / Reconciliación de estados — KAN-119

Owner: Elizabeth. Cross-review: Yohanna. Date: 19 November 2026.
Code snapshot: `dev@c59d201ddcb92ad6043bb3fad056e8a324deaea7`.

**ES:** documentación técnica completada para revisión; la tarea sigue **BLOCKED** por validación histórica/funcional pendiente. No se afirma una máquina general de transiciones, una API de admisión ni aceptación de Melissa de todo el TO-BE.

**EN:** technical reconciliation prepared for review; the ticket remains **BLOCKED** on outstanding historical/functional validation. It does not certify a general transition engine, admission API or client acceptance of the complete TO-BE.

| Rule / Regla | Recorded PO decision / Decisión PO | Current code / Código en la base | Validation boundary / Límite |
|---|---|---|---|
| Call to selection / Convocatoria | Ends preselection even with open requirement reviews | KAN-153: `enviada` or `requisitos_en_revision` → `convocada`; KAN-128 reviews do not change stage | The 6 November clarification locates the end of preselection at withdrawal or call to selection; product rules refine it |
| Express withdrawal / Retirada | Available during preselection and selection (PO 19/11); after admission belongs to enrollment | `retirada_expresa` is allowed from configured open preselection/selection stages | Withdrawal from `lista_espera` remains undecided; no enrollment withdrawal flow is claimed |
| Silence alerts / Alertas de silencio | Light at 2 unanswered contacts; action at 4 and 30 days, configurable per call (PO 19/11) | Read-only evaluation; action threshold requires unanswered attempts and days since the last; answer/postponement restarts | Exact operational threshold is PO demo design; do not attribute those numbers to historical Melissa practice |
| Confirmed silence / Silencio confirmado | Human decision; stage `retirada` (PO 19/11) | Distinct decision/evidence from voluntary withdrawal, same aggregate stage | No timer closes an application automatically |
| Policy editors / Configuración | Admin and captación in programme scope (PO 19/11) | `calls.configure` checked server-side | No universal permission-management UI exists |
| Interview → deliberation / Entrevista → deliberación | Human review and accountable evidence | Stage vocabulary exists; no general selection transition engine | Board mapping remains a proposal; `convocada` alone does not prove the interview happened |
| Admission / Admisión | Selection and coordination by default; configurable permissions (PO 19/11) | Local candidate guards/contracts only; no persisted admission service | Exact signer/quorum, capacity unit/reservation/release and successor schema remain pending |
| Waitlist vacancy / Vacante | Reference order; relevant predefined call criteria and justified exception; fresh human decision | No automatic promotion or seat allocation | No invented ranking policy, automatic admission or enrollment |
| Documents / Documentación | Versioned per call; incidents return to human review | No versioned post-admission document process | Do not automatically revoke admission or require universal signed consent |
| Enrollment / Matrícula | Separate from admission; coder invited by the team at enrollment (PO 19/11) | Existing Enrollment mapping; no admission→enrollment transaction/invitation | Model presence is not a running flow |
| Applicant access / Acceso aspirante | Public registration creates CRM profile; no account/platform access (PO 19/11) | Synthetic applicant account and own-application access still exist in dev | Requires access/auth/seed/UI/E2E changes in the relevant tickets; not implemented here |
| Shared board / Tablero | Seven columns and team edits (PO 19/11) | No connected general board/stage engine | Automation/move rules remain pending; admission/non-admission always require human decision |

## Evidence and sources / Evidencia y fuentes

- **CODE_PRESENT_NOT_RUN in this documentary check:** inspected `api/app/modules/preselection/{models,service,router}.py`, `api/app/core/authz.py`, admissions/requirements models and schemas, and `docs/reports/KAN-153-preselection-closure.md` at the pinned SHA. Runtime results for other branches are not presented as execution of this document.
- **ES:** contrastados los comentarios Jira KAN-119 (10024, 10037, 10059, 10098, 10113), KAN-147 (10100), las aclaraciones de Melissa del 06/11 y el AS-IS v1.0, localizados en Drive. Son fuentes históricas; no confirman por sí solas las decisiones posteriores. La Ronda 3 del 19/11 contiene preguntas/propuestas, no respuestas aprobadas.
- **EN:** checked Jira comments, the 6 November clarification and AS-IS v1.0 located in Drive. Historical sources do not approve later product decisions. The 19 November Round 3 document contains questions/proposals, not confirmed answers.
- **ES:** decisiones actuales de acceso, invitaciones, tablero y código documentadas en `docs/producto/decisiones-po-2026-11-19-acceso-tablero.md` en la rama `ccr-e218aef4-6l29zo@cb62c93`, confirmadas por Elizabeth en esta revisión. Los correos automáticos de estado fueron confirmados por Melissa el 19/11 **según la PO**; no se inventa acta ni se amplía esa confirmación al quórum.
- **EN:** Elizabeth confirmed the access/board decisions recorded on the named branch. Status emails were confirmed by Melissa on 19 November **as reported by the PO**; this is not evidence of approval of the admission quorum.

## Remaining acceptance / Aceptación pendiente

**ES:** Yohanna revisa la reconciliación; la PO y Melissa resuelven los puntos históricos aplicables y la autoridad/quórum/cupos. La Ronda 3 propone dos firmantes (selección y coordinación), pero lo pregunta para confirmar: no se convierte en valor aprobado. Asistencia/migración académica queda con Claude por instrucción de Elizabeth. No se cierran KAN-119 ni las tareas de admisión por publicar este informe.

**EN:** Yohanna reviews this reconciliation. PO/client resolve applicable historical points and exact authority/quorum/capacity policy. Round 3 proposes two signers and asks for confirmation; it is not an approved default. Claude owns the academic migration follow-up per Elizabeth. Publishing this report does not close KAN-119 or admission work.
