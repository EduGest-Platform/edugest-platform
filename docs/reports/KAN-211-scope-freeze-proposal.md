# KAN-211 — Propuesta de alcance / Scope freeze proposal

27/11/2026 · Discussion 30/11/2026 · Owner Elizabeth · Reviewer Yohanna.
PROPOSED — not an approved freeze change. Sources: KAN-211 PO comment 27/11, CONSTITUTION.md, AGENTS.md, projectplan.md, contribution.md.

## ES
El ticket menciona 27/11 18:00 salvo P0; el comentario PO del 27/11 traslada la revisión conjunta al 30/11, no aprueba fecha nueva. El repositorio conserva freeze de desarrollo 04/12, ensayo 09/12 y defensa 10/12. Propuesta: congelar nuevos incrementos de alcance al acordar el baseline; hasta 04/12 permitir integración, correcciones y validación de alcance acordado. No modificar unilateralmente fechas ni reglas.

### Propuesta de baseline
| Grupo | Alcance propuesto | Condición de aceptación |
|---|---|---|
| P0 | Admisión humana, espera, matrícula, cupos, permisos y seguridad | KAN-112/143/147/156/163/164/175; #300 evidencia parcial, no implementación; reconciliar política y datos |
| P0 | Autenticación por ámbito, auditoría, seguridad de demo | KAN-35/37/73; sin credenciales por defecto ni datos reales; pruebas negativas |
| P1 | Personal y tablero | #270/#271 integrados, CI/E2E PASS; KAN-38/51/222/244 abiertos; no ampliar permisos |
| P1 | Alertas y feedback docente | #273/#274 abiertos; integrar tras resolver conflictos y CI/E2E, evidencia sintética y publicación humana |
| P1 | Documentación/demo | #288/#289: reconciliar navegación y flujo de matrícula con dev y política; revisión visual |
| Opcional | #290 tema/idioma | Solo alcance parcial aceptado, accesibilidad y no regresiones; no prometer traducción completa |
| Diferir salvo acuerdo | #276 Zoom, #278 correo, #279 eventos | Draft, sin activación externa; no retrasar recorrido principal |

Estado al consultar: #270/#271 merged; #273/#274/#300 abiertos; #276/#278/#279/#290 Draft. No es inventario exhaustivo de todos los tickets: el equipo debe revisar backlog completo y capacidad el lunes. KAN-256 verificará briefing/criterios; no declarar porcentaje de automatización 70% medido sin validación.

### Agenda de decisión del lunes (propuesta 30 min)
5 min estado real y bloqueantes; 10 min recorrido demo y criterios imprescindibles; 10 min clasificación de tickets (incluido/diferido/bloqueado, owner y reviewer); 5 min confirmar fechas, excepciones P0 y acta. Registrar decisión PO, acuerdo SM/equipo, responsables, criterio de aceptación y PR/evidencia; las discrepancias se mantienen abiertas.

### Gate
Antes de merge: revisión cruzada, CI del HEAD, contratos/migraciones si aplican, pruebas negativas y sintéticas. Antes de demo: smoke del entorno autorizado, recorrido principal de punta a punta, datos sintéticos, fallback seguro y guion. No abrir nuevo alcance sin decisión PO/SM documentada; no hacer despliegue sin autorización. Tras freeze, tratar excepciones según acuerdo aprobado. KAN-211 solo se cierra con decisión documentada y revisión cruzada, no por este borrador.

## EN
The 27 Nov issue wording conflicts with the canonical 4 Dec development freeze; the PO moved the discussion to 30 Nov without approving a changed gate. Proposed baseline: prioritize human admissions/enrollment, scoped access and demo security; finish already-scoped staff/discussion/alerts/feedback and accurate documentation; optional appearance only if validated; defer Zoom, email and Events unless explicitly accepted. Review the full backlog and capacity at the Monday meeting, record included/deferred/blocked scope, owners, reviewers, dates and P0 exceptions. Keep 4 Dec freeze, 9 Dec rehearsal and 10 Dec defence unless a documented decision changes them. No unilateral approval, no deployment, no claim of measured 70% savings. This report is a proposal, not completion.
