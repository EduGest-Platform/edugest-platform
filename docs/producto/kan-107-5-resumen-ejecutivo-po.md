# KAN-107 · Resumen para la Product Owner / PO summary (revisión V2, 17/11/2026)

> **EN:** Revised design for PO/Anas review only; no code, database migration or API contract changed; documents: KAN-107 design, documentation branch `docs/KAN-107-data-governance` into `dev`. Dynamic per-call protected-field access is proposed but not implemented. The backend owner must coordinate any future schema change in KAN-42 with the existing Alembic chain.

**Qué está hecho**
- Diccionario consolidado (14 campos de Anas + campos de EduGest): `kan-107-1-…`
- Versionado de formularios **de candidatura** por convocatoria (propuesta `form_version`; integridad y publicación definidas): `kan-107-2-…`
- Evaluación de privacidad (18 riesgos, R1–R18, estado de decisiones): `kan-107-3-…`
- Plan por archivo, orden y pruebas existentes/propuestas: `kan-107-4-…`

**Decisiones funcionales (17/11 y aceptación PO 18/11; no son validación jurídica)**
- Se mantienen nacionalidad, país de nacimiento y género en el **diseño sintético** por decisión PO. **Están observados en el formulario del bootcamp; la exigencia contractual del financiador sigue por confirmar con Melissa**.
- Situación actual configurable por convocatoria; en el MVP se simula con seed sintético.
- Disponibilidad opcional; nombre y apellidos separados; "cómo nos has conocido" **propuesto** opcional con "otros", pendiente de ratificación.
- **Bootcamp 1.250 h (PO 18/11):** conocimientos de programación incluyendo formación/autoaprendizaje, sin exigir experiencia profesional; motivación inicial opcional en diseño, profundizada en entrevista.
- **Edad por convocatoria aceptada en diseño:** mayoría de edad para bootcamp; B publica más de 16; fecha de comprobación e interpretación exacta de B pendientes.
- **Residencia obligatoria para bootcamp 1.250 h (PO 18/11)** por requisito publicado en Comunidad de Madrid; revisión humana. Otras convocatorias sin finalidad territorial siguen pendientes.
- **Acceso funcional dinámico:** rol + ámbito de convocatoria + categoría de datos + concesión temporal. Captación/selección pueden tener acceso operativo conforme a sus funciones; los campos G3/G6 requieren habilitación expresa. Administrar permisos no equivale a poder leer todos los datos. Los derechos de la persona solicitante se gestionan separadamente.
- **No se programan cuotas ni prioridades de admisión** basadas en género, nacionalidad o vulnerabilidad mientras no haya requisitos y legalidad documentados; la revisión humana por sí sola no los legitima.

**Riesgos que quedan**
1. Uso de género/nacionalidad en cuotas y prioridades: documentarlo por convocatoria y que lo valide la Fundación (R3, R11).
2. "Discapacidad" y otras situaciones: probable dato de salud; la Fundación debe valorarlo antes de datos reales (R4).
3. Con solo el año de nacimiento no se prueba la edad exacta ante ningún umbral por convocatoria (R12).
4. Datos sensibles en notas CRM (R7).
5. Fuentes oficiales generales verificadas documentalmente (EUR-Lex/AEPD), pero **sin validación jurídica específica**; pruebas de implementación no ejecutadas.
6. La gestión de concesiones/revocaciones por categoría **todavía no existe en la API** y debe implementarse y probarse bajo KAN-42.

**Pendiente y fuera del alcance (se anota en `docs/producto/README.md`)**
Responsable del tratamiento y DPO · base jurídica · plazos de conservación · proceso de rectificación/borrado (hoy por correo) · EIPD · verificación legal.

**Qué necesita confirmar Melissa**
Confirmar exigencias contractuales, finalidad real de país/nacionalidad/género, opciones de género y situación actual, y cualquier criterio diferencial de selección. Esto **no bloquea documentación/demo sintética**, pero sí su uso real o configuración de cuotas.

**Qué debe implementar el equipo (tras aprobar el diseño)**
Backend bajo KAN-42: pasos A–D, incluida **autorización por categoría y convocatoria**, tras revisión de la secuencia única Alembic. **No crear migraciones desde KAN-107 ni reservar nombres/IDs.** Anas: paso E, formulario basado en definición pública y `pnpm gen:api`. Resolver con PO si coexisten contacto e inscripción 15 h y qué opciones del selector B crean `Application`/`call_id`; se retira la separación obligatoria como lead. C sigue sin verificar; certificado de discapacidad y entidad de derivación propuestos en G6, sin ampliar alcance aprobado. Ver Entregable 4 y Entregable 6.

**Qué puede considerarse finalizado en KAN-107**
Solo el **análisis y diseño**, después de revisión de Anas y aceptación formal PO, trazabilidad de fuentes y PR documental cuando esté autorizado. No están terminadas la implementación, migraciones, control de acceso dinámico ni validación jurídica. Este paquete: Diseño KAN-107, rama documental `docs/KAN-107-data-governance` hacia `dev`. No modificar Jira a Done por esta entrega.

**Decisión sobre migraciones (sin ambigüedad):** Jira contiene una secuencia prevista de admisión → documentos RAG → académico → alertas. Actualmente el diseño **no crea ninguna migración**. Backend incorpora el cambio de KAN-42 a la única cadena compartida cuando llegue su turno, mirando `alembic heads`, no adivinando nombres ni forzando números. Nadie del equipo (persona o agente de IA) genera `revision` ni `down_revision` bajo KAN-107. En `dev` (19/11/2026, `c4e385c`) la cadena Alembic integrada es `0001_f1_cimientos` → `0003_rag_knowledge` → `0004_requirement_reviews_and_revision_history` → `0006_call_requirements`, con una sola cabeza (`0006`). No existe `0002`; la `0005` de KAN-153 está en revisión y se encadena tras `0006`. Los números no son un orden cronológico: Alembic sigue `down_revision`.

**Aclaración de funcionamiento:** los permisos sensibles pueden otorgarse/revocarse **durante** la convocatoria sin crear otra versión de formulario. Requieren autoridad administrativa, aprobación, motivo, expiración y auditoría; no están programados en el backend actual.


## Decisión PO del 18/11/2026 / PO decision of 18/11/2026

**ES:** la copia canónica de la decisión (bootcamp de 1.250 h y recomendaciones asociadas), con su evidencia y lo que sigue pendiente, está en el [Entregable 1](kan-107-1-diccionario-datos-consolidado.md#decisión-po-aceptada-el-18112026--po-decision-accepted-on-18112026). No se repite aquí para evitar divergencias.

**EN:** the canonical copy of the decision (1,250-hour bootcamp and associated recommendations), with evidence and pending items, is in [Deliverable 1](kan-107-1-diccionario-datos-consolidado.md#decisión-po-aceptada-el-18112026--po-decision-accepted-on-18112026). It is not repeated here to avoid drift.

## English edition (equivalent sections, KAN-107 V2)

**Done.** Consolidated dictionary (14 fields from Anas's inventory plus EduGest fields), per-call form versioning, preliminary privacy assessment, implementation plan and a dynamic access annex. All are documents of the KAN-107 design, documentation branch `docs/KAN-107-data-governance` into `dev`.

**Updated source.** KAN-92/93 inventory is now in `dev` via #27; KAN-107 adds governance without duplicating it. The current B evidence supersedes the inconclusive contact screenshot; routing remains a PO decision. C is unverified; certificate status and referring entity are proposed G6. KAN-105 logging is present (not run here); retention must align with KAN-209/#25. Anas cross-review and PO acceptance remain pending.

**Decisions already taken (functional, not legal).** Keep nationality, country of birth and gender in the synthetic design; options configurable per call; availability optional; split first/last name. No quotas, priorities or exclusions are approved.

**To be confirmed.** Funder requirements and purposes (Melissa/Foundation); exact age operator/reference date (per-call configuration and bootcamp adulthood accepted in design); 15-hour application/contact routing and B/C minimum fields; "How did you hear about us" optional; implementation of PO-accepted optional initial `motivacion` (still mandatory in API/DB); residence in calls without a territorial requirement.

**To be implemented by the team (after design approval).** Backend under KAN-42 (steps A–D, including category- and call-level authorisation) coordinating the single Alembic chain; Anas step E. KAN-107 creates no migrations.

**What can be considered finished in KAN-107.** Only analysis and design, after Anas's review of the corrected version and Elizabeth's acceptance. The design can be closed for the synthetic demo with the Foundation's validation kept as an explicit condition for processing real data. Jira must not be moved to Done by this delivery.
