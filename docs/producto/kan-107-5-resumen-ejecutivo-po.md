# KAN-107 · Resumen para la Product Owner / PO summary (revisión V2, 17/11/2026)

> **EN:** Revised design for PO/Anas review only; no code, database migration or API contract changed; the documents are under review in PR #24 (open, not merged). Dynamic per-call protected-field access is proposed but not implemented. The backend owner must coordinate any future schema change in KAN-42 with the existing Alembic chain.

**Qué está hecho**
- Diccionario consolidado (14 campos de Anas + campos de EduGest): `kan-107-1-…`
- Versionado de formularios **de candidatura** por convocatoria (propuesta `form_version`; integridad y publicación definidas): `kan-107-2-…`
- Evaluación de privacidad (14 riesgos, estado de decisiones): `kan-107-3-…`
- Plan por archivo, orden y pruebas existentes/propuestas: `kan-107-4-…`

**Decisiones confirmadas (equipo, 17/11, funcionales; no son validación jurídica)**
- Se mantienen nacionalidad, país de nacimiento y género en el **diseño sintético** por decisión PO. **Están observados en el formulario del bootcamp; la exigencia contractual del financiador sigue por confirmar con Melissa**.
- Situación actual configurable por convocatoria; en el MVP se simula con seed sintético.
- Disponibilidad opcional; nombre y apellidos separados; "cómo nos has conocido" opcional con "otros".
- Se mantiene la experiencia en programación; edad mínima 18.
- Residencia: se pide siempre; el requisito depende de la convocatoria y lo confirma una persona.
- **Acceso funcional dinámico:** rol + ámbito de convocatoria + categoría de datos + concesión temporal. Captación/selección pueden tener acceso operativo conforme a sus funciones; los campos G3/G6 requieren habilitación expresa. Administrar permisos no equivale a poder leer todos los datos. Los derechos de la persona solicitante se gestionan separadamente.
- **No se programan cuotas ni prioridades de admisión** basadas en género, nacionalidad o vulnerabilidad mientras no haya requisitos y legalidad documentados; la revisión humana por sí sola no los legitima.

**Riesgos que quedan**
1. Uso de género/nacionalidad en cuotas y prioridades: documentarlo por convocatoria y que lo valide la Fundación (R3, R11).
2. "Discapacidad" y otras situaciones: probable dato de salud; la Fundación debe valorarlo antes de datos reales (R4).
3. Con solo el año de nacimiento no se prueba la mayoría de edad exacta (R12).
4. Datos sensibles en notas CRM (R7).
5. Fuentes oficiales generales verificadas documentalmente (EUR-Lex/AEPD), pero **sin validación jurídica específica**; pruebas de implementación no ejecutadas.
6. La gestión de concesiones/revocaciones por categoría **todavía no existe en la API** y debe implementarse y probarse bajo KAN-42.

**Pendiente y fuera del alcance (se anota en `docs/producto/README.md`)**
Responsable del tratamiento y DPO · base jurídica · plazos de conservación · proceso de rectificación/borrado (hoy por correo) · EIPD · verificación legal.

**Qué necesita confirmar Melissa**
Confirmar exigencias contractuales, finalidad real de país/nacionalidad/género, opciones de género y situación actual, y cualquier criterio diferencial de selección. Esto **no bloquea documentación/demo sintética**, pero sí su uso real o configuración de cuotas.

**Qué debe implementar el equipo (tras aprobar el diseño)**
Backend bajo KAN-42: pasos A–D, incluida **autorización por categoría y convocatoria**, tras revisión de la secuencia única Alembic. **No crear migraciones desde KAN-107 ni reservar nombres/IDs.** Anas: paso E, formulario basado en definición pública y `pnpm gen:api`. No mezclar formulario de contacto 15 h con `Application`. Ver Entregable 4 y Entregable 6.

**Qué puede considerarse finalizado en KAN-107**
Solo el **análisis y diseño**, después de revisión de Anas y aceptación formal PO, trazabilidad de fuentes y PR documental cuando esté autorizado. No están terminadas la implementación, migraciones, control de acceso dinámico ni validación jurídica. Este paquete está en el [PR #24](https://github.com/EduGest-Platform/edugest-platform/pull/24) (abierto hacia `dev`, pendiente de revisión; no fusionado). No modificar Jira a Done por esta entrega.

**Decisión sobre migraciones (sin ambigüedad):** Jira contiene una secuencia prevista de admisión → documentos RAG → académico → alertas. Actualmente el diseño **no crea ninguna migración**. Backend incorpora el cambio de KAN-42 a la única cadena compartida cuando llegue su turno, mirando `alembic heads`, no adivinando nombres ni forzando números. Claude no debe generar `revision` ni `down_revision` para KAN-107.

**Aclaración de funcionamiento:** los permisos sensibles pueden otorgarse/revocarse **durante** la convocatoria sin crear otra versión de formulario. Requieren autoridad administrativa, aprobación, motivo, expiración y auditoría; no están programados en el backend actual.

## English edition (equivalent sections, KAN-107 V2)

**Done.** Consolidated dictionary (14 fields from Anas's inventory plus EduGest fields), per-call form versioning, preliminary privacy assessment, implementation plan and a dynamic access annex. All are documents under review in [PR #24](https://github.com/EduGest-Platform/edugest-platform/pull/24) (open, not merged).

**Decisions already taken (functional, not legal).** Keep nationality, country of birth and gender in the synthetic design; options configurable per call; availability optional; split first/last name. No quotas, priorities or exclusions are approved.

**To be confirmed.** Funder requirements and purposes (Melissa/Foundation); minimum age 18; "How did you hear about us" optional; whether `motivacion` becomes optional (it is mandatory in the current contract); residence in calls without a territorial requirement.

**To be implemented by the team (after design approval).** Backend under KAN-42 (steps A–D, including category- and call-level authorisation) coordinating the single Alembic chain; Anas step E. KAN-107 creates no migrations.

**What can be considered finished in KAN-107.** Only analysis and design, after Anas's review of the corrected version and Elizabeth's acceptance. The design can be closed for the synthetic demo with the Foundation's validation kept as an explicit condition for processing real data. Jira must not be moved to Done by this delivery.
