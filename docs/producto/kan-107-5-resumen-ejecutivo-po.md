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
- Disponibilidad opcional; nombre y apellidos separados; «cómo nos conociste» obligatorio con opción `other` (PO 19/11).
- **Bootcamp 1.250 h (PO 18/11):** conocimientos de programación incluyendo formación/autoaprendizaje, sin exigir experiencia profesional; motivación inicial opcional en diseño, profundizada en entrevista.
- **Edad (PO 19/11):** al inicio del curso; bootcamp mayoría de edad y B `gte` 16. Año insuficiente → revisión humana.
- **Residencia (PO 18–19/11):** Madrid obligatoria en el bootcamp; otras convocatorias configuradas según lo publicado, con revisión humana.
- **Acceso funcional (PO 19/11):** administración/selección leen G3/G6 por defecto dentro de su ámbito; otros perfiles requieren concesión vigente gestionada por administración y auditada. La ampliación posterior de coordinación pertenece a su matriz de acceso. Ninguno omite ámbito/finalidad; KAN-107 no habilita permisos live.
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
Backend bajo KAN-42: pasos A–D, incluida autorización por categoría y convocatoria y la política PO 19/11, tras revisar la cadena única Alembic. KAN-107 no crea migraciones ni reserva IDs. Anas: formulario desde definición pública y cliente generado. B: fecha concreta → candidatura; organizar/avisar → contacto. C queda fuera del MVP; cualquier futura inclusión requiere fuente, necesidad y controles G6. Ver Entregables 4 y 6.

**Qué puede considerarse finalizado en KAN-107**
Solo el **análisis y diseño**, después de revisión de Anas y aceptación formal PO, trazabilidad de fuentes y PR documental cuando esté autorizado. No están terminadas la implementación, migraciones, control de acceso dinámico ni validación jurídica. Este paquete: Diseño KAN-107, rama documental `docs/KAN-107-data-governance` hacia `dev`. No modificar Jira a Done por esta entrega.

**Decisión sobre migraciones:** KAN-107 es diseño y no crea revisiones ni reserva IDs. Backend coordina KAN-42 desde la cabeza real, preservando revisiones integradas. En `dev@c59d201` (19/11/2026), la cadena integrada es `0001 → 0003 → 0004 → 0006 → 0007 → 0005`, cabeza única `0005`. KAN-128, KAN-135, KAN-183 y KAN-153 están integrados. No existe `0002`; Alembic sigue `down_revision`, no el orden numérico. Asistencia y alertas aún no tienen migraciones integradas. / At this pinned dev snapshot the single head is `0005`; no academic or alert migration is integrated.

**Aclaración de funcionamiento:** los permisos sensibles pueden otorgarse/revocarse **durante** la convocatoria sin crear otra versión de formulario. Requieren autoridad administrativa, aprobación, motivo, expiración y auditoría; no están programados en el backend actual.


## Decisión PO del 18/11/2026 / PO decision of 18/11/2026

**ES:** la copia canónica de la decisión (bootcamp de 1.250 h y recomendaciones asociadas), con su evidencia y lo que sigue pendiente, está en el [Entregable 1](kan-107-1-diccionario-datos-consolidado.md#decisión-po-aceptada-el-18112026--po-decision-accepted-on-18112026). No se repite aquí para evitar divergencias.

**EN:** the canonical copy of the decision (1,250-hour bootcamp and associated recommendations), with evidence and pending items, is in [Deliverable 1](kan-107-1-diccionario-datos-consolidado.md#decisión-po-aceptada-el-18112026--po-decision-accepted-on-18112026). It is not repeated here to avoid drift.

## English edition (equivalent sections, KAN-107 V2)

**Done.** Consolidated dictionary (14 fields from Anas's inventory plus EduGest fields), per-call form versioning, preliminary privacy assessment, implementation plan and a dynamic access annex. All are documents of the KAN-107 design, documentation branch `docs/KAN-107-data-governance` into `dev`.

**Updated source.** KAN-92/93 inventory is now in `dev` via #27; KAN-107 adds governance without duplicating it. The current B evidence supersedes the inconclusive contact screenshot; routing remains a PO decision. C is unverified; certificate status and referring entity are proposed G6. KAN-105 logging is present (not run here); retention must align with KAN-209/#25. Anas cross-review and PO acceptance remain pending.

**Decisions already taken (functional, not legal).** Keep nationality, country of birth and gender in the synthetic design; options configurable per call; availability optional; split first/last name. No quotas, priorities or exclusions are approved.

**To be confirmed.** Foundation purposes, legal basis, funder requirements and real-data conditions. The PO settled synthetic-design age, B routing, referral source, residence, 24-hour grace and G3/G6 access on 19 November; see the canonical decision in Deliverable 1. Cross-review and implementation remain separate.

**To be implemented by the team (after design approval).** Backend under KAN-42 (steps A–D, including category- and call-level authorisation) coordinating the single Alembic chain; Anas step E. KAN-107 creates no migrations.

**What can be considered finished in KAN-107.** Only analysis and design, after Anas's review of the corrected version and Elizabeth's acceptance. The design can be closed for the synthetic demo with the Foundation's validation kept as an explicit condition for processing real data. Jira must not be moved to Done by this delivery.
