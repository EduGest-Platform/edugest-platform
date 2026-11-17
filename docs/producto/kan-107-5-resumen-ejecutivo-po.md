# KAN-107 · Resumen para la Product Owner / PO summary (17/11/2026)

> **EN:** Analysis and design for KAN-107 is ready for review. No code, model, migration or contract was changed. Legal validation is out of scope (free proof of concept, synthetic data) and belongs to the Foundation later.

**Qué está hecho**
- Diccionario consolidado (14 campos de Anas + campos de EduGest): `kan-107-1-…`
- Versionado por convocatoria (1 tabla `form_version` con JSON inmutable): `kan-107-2-…`
- Evaluación de privacidad (14 riesgos, estado de decisiones): `kan-107-3-…`
- Plan por archivo, orden y pruebas existentes/propuestas: `kan-107-4-…`

**Decisiones confirmadas (equipo, 17/11, funcionales; no son validación jurídica)**
- Se mantienen nacionalidad, país de nacimiento y género (el financiador los exige; figuran en la web de Somos F5).
- Situación actual configurable por convocatoria; en el MVP se simula con seed sintético.
- Disponibilidad opcional; nombre y apellidos separados; "cómo nos has conocido" opcional con "otros".
- Se mantiene la experiencia en programación; edad mínima 18.
- Residencia: se pide siempre; el requisito depende de la convocatoria y lo confirma una persona.
- Ven los datos: selección, preselección/captación y administración. No coder, alumno ni aspirante.
- Género y vulnerabilidad pueden pesar en la revisión (cuotas, prioridades), nunca como criterio único ni automático.

**Riesgos que quedan**
1. Uso de género/nacionalidad en cuotas y prioridades: documentarlo por convocatoria y que lo valide la Fundación (R3, R11).
2. "Discapacidad" y otras situaciones: probable dato de salud; la Fundación debe valorarlo antes de datos reales (R4).
3. Con solo el año de nacimiento no se prueba la mayoría de edad exacta (R12).
4. Datos sensibles en notas CRM (R7).
5. Fuentes jurídicas no verificadas y pruebas no ejecutadas.

**Pendiente y fuera del alcance (se anota en `docs/producto/README.md`)**
Responsable del tratamiento y DPO · base jurídica · plazos de conservación · proceso de rectificación/borrado (hoy por correo) · EIPD · verificación legal.

**Qué necesita confirmar Melissa**
Ratificar las respuestas anteriores y aportar las opciones reales de situación por convocatoria cuando sea posible. No bloquea el MVP.

**Qué debe implementar el equipo (tras aprobar el diseño)**
Backend: pasos A–D (sin permisos nuevos). Anas: paso E (formulario desde la definición, `pnpm gen:api`). Orden en el Entregable 4.

**Qué puede considerarse finalizado en KAN-107**
El **análisis y diseño** (CA1–CA5), cuando la PO lo revise (CA6). No finalizado: implementación y validación legal. Este PR no cambia Jira ni se fusiona sin revisión humana.
