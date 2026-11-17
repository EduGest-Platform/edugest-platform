# KAN-107 · Resumen para la Product Owner / PO summary (17/11/2026)

> **EN:** Analysis and design for KAN-107 is ready for review. No code, model, migration or contract was changed. Several points need Melissa/DPO before real data.

**Qué está hecho**
- Diccionario consolidado (14 campos de Anas + campos de EduGest) con entidad destino, acceso y estado: `kan-107-1-…`
- Propuesta de versionado por convocatoria (1 tabla `form_version` + JSON inmutable): `kan-107-2-…`
- Evaluación de privacidad con 14 riesgos y 9 decisiones pendientes: `kan-107-3-…`
- Plan por archivo, orden, pruebas existentes/propuestas: `kan-107-4-…`

**Decisiones confirmadas (tuyas, 17/11, funcionales)**
Mantener nacionalidad, país de nacimiento y género · situación actual configurable por convocatoria · disponibilidad opcional · nombre y apellidos separados. Se han respetado todas; no son una validación jurídica.

**Riesgos que quedan**
1. Sin base jurídica ni plazos de conservación confirmados (R2, R9).
2. Nacionalidad, país de nacimiento y género: sin exigencia del financiador acreditada; si se mantienen, solo para estadística y fuera de preselección (R3).
3. "Discapacidad" y otras situaciones: probable dato de salud (art. 9); requiere condición adicional del DPO (R4).
4. Datos sensibles en notas CRM (R7).
5. Fuentes jurídicas citadas **sin verificar en línea** (B3); las pruebas no se han ejecutado (B6).

**Qué necesita confirmar Melissa** (detalle D1–D9 en el Entregable 3)
¿Quién es responsable y qué base jurídica? · ¿El financiador exige nacionalidad, país de nacimiento y género? · ¿Qué opciones de situación exige cada financiador? · plazos de conservación · edad mínima · quién ve datos sensibles · ¿EIPD? · ¿se mantiene `motivacion`? · ¿la residencia en Madrid es revisión o elegibilidad?

**Qué debe implementar el equipo (tras aprobar el diseño)**
Backend: pasos A–D (nombre/apellidos, `form_version`, validación, datos sensibles con permiso propio). Anas: paso E (formulario desde la definición, `pnpm gen:api`). Orden y riesgos de migración en el Entregable 4. El paso D queda bloqueado hasta las respuestas de Melissa.

**Qué puede considerarse finalizado en KAN-107**
Solo el **análisis y diseño**: diccionario, versionado, privacidad y plan (CA1–CA5), **cuando tú los revises (CA6)**. No finalizado: implementación, decisiones jurídicas (CA7) y verificación de fuentes. Este PR no cambia el estado de Jira ni se fusiona sin revisión humana.
