# KAN-222 — Autoridad de invitación / Invitation authority

27/11/2026 · Elizabeth · Reviewer Yohanna · Status PROPOSED / BLOCKED on PO clarification.

## ES
Fuente: comentario PO en KAN-222 (27/11): Fundación puede enviar invitaciones para incorporar una persona; Administración gestiona registro/alta; enviar no concede roles. Sigue abierta la pregunta de qué autorización debe existir antes de enviar.

Estado observado tras #270: api/app/modules/staff/service.py: create_invitation exige require_admin; renew/revoke usan locked_invitation con require_admin. invitation_directory.py exige require_admin. policy.py limita autoridad a administración global. authz.py no concede emisión a captacion. El endpoint emite código para una cuenta interna existente, no crea cuenta ni envía correo. Por tanto no equivale a la política futura de invitación delegada.

### Propuesta para decisión PO (no aprobada)
1. Fundación autenticada y con permiso específico de alcance podrá iniciar una solicitud de incorporación o entregar una invitación ya autorizada por Administración mediante canal aprobado; nunca antes de disponer de autorización para esa acción.
2. Por defecto, emisión/renovación/revocación del código y alta administrativa siguen en Administración. Si PO desea emisión directa por Fundación, definir permiso independiente y ámbito explícito, destinatario elegible, caducidad, auditoría y mecanismo de aprobación; no reutilizar admin ni conceder acceso global.
3. Aceptación vinculada a identidad destinataria; no concede RoleAssignment. Elevación solicitada, revisión por tercero autorizado y aplicación explícita; revocación trazable. Aspirantes/coders/alumni no pueden invitar.
4. Sin correo real ni alta nueva hasta aprobar canal, privacidad y flujo; no ampliar el MVP sin acuerdo de capacidad.

### Criterios de aceptación de la decisión
- PO elige entrega de invitación administrativa vs emisión delegada; concreta si se requiere permiso activo específico antes de enviar, ámbito y quién autoriza destinatario.
- Casos futuros si cambia implementación: captación autorizada en ámbito permite acción; sin permiso, ámbito ajeno, roles externos y anónimo se rechazan 401/403; token caducado, revocado, reutilizado o ajeno se rechaza; invitar/aceptar no cambia roles; auditoría sin código/hash ni PII adicional.
- Revisión Yohanna de seguridad y trazabilidad, pruebas sintéticas pertinentes si se implementa. KAN-38/KAN-225 dependen de la aclaración. No declarar Done por este documento.

## EN
PO's recorded clarification allows Foundation staff to send an invitation while Administration controls registration; sending grants no privilege. Current server issuance, renewal, revocation and directory require global administration; the code targets existing internal accounts and does not send mail. Proposed conservative default: authorized Foundation staff can request onboarding or deliver an already-authorized invitation, not issue a token without explicit permission. If delegated issuance is selected, introduce a narrowly scoped permission and test positive/negative authorization, token lifecycle, separation of roles and audit. PO must decide delivery versus issuance, active permission, scope and recipient authorization; cross-review is required. No implementation or real delivery in this document. #270 CI/E2E passed historically; this is a static policy reconciliation, NOT_RUN locally.
