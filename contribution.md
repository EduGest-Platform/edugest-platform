# contribution.md — Team contribution rules / Reglas de contribución V3

**As of 11/11/2026:** Yohanna is Scrum Master + automation developer; Elizabeth is Product Owner + backend developer; David RAG; Anas frontend; Abdur only dropout ML. Task allocation and dates are proposed until capacity is agreed.

## ES — Flujo de colaboración

1. El PO (Elizabeth) ordena el Product Backlog, valida requisitos y acepta historias. La Scrum Master (Yohanna) facilita Sprint Planning, Daily Scrum, Review, Retro y elimina impedimentos.
2. Cada cambio parte de un ticket con historia, criterios de aceptación, dependencias, owner, revisor diferente, datos sintéticos y evidencia. Nadie mueve un ticket a Done solo por existir código.
3. Ramas cortas `feat/`, `fix/`, `test/`, `docs/`; PRs de alcance limitado, revisar diff, pruebas, API y migraciones. No hacer merges directos en `main` sin acuerdo del equipo.
4. **Código y identificadores en inglés**; READMEs, manuales y documentación de entrega a GitHub en español e inglés. No bifurcar la misma regla en archivos contradictorios.
5. Revisor por dominio: Elizabeth (API/datos/permisos); Anas (frontend/UX); David (RAG y feedback IA); Abdur (solo modelos de abandono); Yohanna (automatización, QA y proceso).
6. Evitar 2 historias de integración crítica a la vez; preferir un caso E2E antes que cinco pantallas de demo sin backend. Dejar constancia de bloqueos, tests no ejecutados y límites.
7. Autorización en **FastAPI por rol y ámbito**; datos sintéticos; cambios de acceso aprobados por personas autorizadas; no confiar en selector «Ver como» o `localStorage`.
8. No utilizar nombre ni logo de la fundación como marca. Se admite inspiración cromática propia. No subir material con licencia o datos personales sin permiso.
9. Sin comandos destructivos sobre bases compartidas, conexiones externas ni despliegues públicos sin aprobación. No crear/cambiar issues Jira, commits o PRs por simple lectura de este plan.
10. Freeze de desarrollo **04/12/2026**, ensayo **09/12**, defensa **10/12**. No reprogramar fuera de plazo sin decisión PO y comunicación SM.

**Definition of Ready / DoR:** valor y usuario, casos, dependencias, owner/reviewer, contrato y criterios objetivos, restricciones RGPD/IA.

**Definition of Done / DoD:** comportamiento y errores probados, autorización negativa, contratos/migraciones actualizados, pruebas ejecutadas o bloqueo visible (entonces NO Done), revisión cruzada, reproducibilidad y documentación.

## EN — Contribution workflow

- PO Elizabeth prioritises and accepts stories; SM Yohanna facilitates Scrum events and resolves blockers.
- Each small PR has one owner, different reviewer, task description, acceptance, related API/schema and evidence of tests.
- Use short branches and no direct merge without review; code identifiers are English, deliverable docs ES/EN.
- Synthetic data only, least privilege in backend, human decisions for admissions, secure read-only assistant tools; ML results not real-world validated.
- Abdur exclusively owns dropout ML and model evaluation; David owns RAG, not the dropout model; Anas owns UI, Elizabeth data/API, Yohanna automations/QA process.
- Deadline for new feature development: 04 Dec; rehearsal 09 Dec; defence 10 Dec. No Jira edits or external deployments without explicit approval.

**Security and safety / Seguridad:** never commit `.env`, tokens, secrets, real records, personal identifiers or private documents. Never generate arbitrary SQL from assistant prompts, or execute student code in the main API process. Any risk score requires explanation and human oversight.
