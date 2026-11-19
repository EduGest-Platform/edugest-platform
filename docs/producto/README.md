# docs/producto — EduGest / Gistar (KAN-107 revisión V2)

**Estado:** documentos de diseño (Diseño KAN-107, rama documental `docs/KAN-107-data-governance` hacia `dev`), para revisión de Anas y aceptación de la PO. Sin cambios de código, OpenAPI, PostgreSQL ni migraciones. Solo datos sintéticos.


## Decisión PO del 18/11/2026 / PO decision of 18/11/2026

**ES:** la copia canónica de la decisión (bootcamp de 1.250 h y recomendaciones asociadas), con su evidencia y lo que sigue pendiente, está en el [Entregable 1](kan-107-1-diccionario-datos-consolidado.md#decisión-po-aceptada-el-18112026--po-decision-accepted-on-18112026). No se repite aquí para evitar divergencias.

**EN:** the canonical copy of the decision (1,250-hour bootcamp and associated recommendations), with evidence and pending items, is in [Deliverable 1](kan-107-1-diccionario-datos-consolidado.md#decisión-po-aceptada-el-18112026--po-decision-accepted-on-18112026). It is not repeated here to avoid drift.

## Revisión del 19/11/2026 / Review of 19/11/2026

**ES:** correcciones de la revisión de Anas: cadena Alembic real de `dev` (`0001 → 0003 → 0004 → 0006`, cabeza única `0006`) en el Entregable 4; KAN-128 reconocido como integrado en el Entregable 6; referencia de notas CRM corregida a R7; recuento de riesgos 18 (R1–R18); la matriz RBAC fechada que no existe en `dev` se sustituye por `docs/reports/KAN-109-f1-rbac-regression.md`; estados de PR abierta sustituidos por la referencia permanente a la rama y la historia; normas de migraciones formuladas para todo el equipo; KAN-124 marcado como integrado para los campos actuales (aceptación pendiente según su informe); la decisión PO del 18/11 queda con una única copia canónica. La PO resolvió el mismo día las decisiones abiertas; constan en [Decisiones PO del 19/11/2026](kan-107-1-diccionario-datos-consolidado.md#decisiones-po-del-19112026--po-decisions-of-19112026). No se implementan cambios de base de datos ni permisos en este paquete.

**EN:** Anas's review fixes: real `dev` Alembic chain in Deliverable 4; KAN-128 acknowledged as merged in Deliverable 6; CRM notes reference fixed to R7; risk count 18 (R1–R18); the dated RBAC matrix that is not in `dev` replaced by `docs/reports/KAN-109-f1-rbac-regression.md`; open-PR status lines replaced by permanent branch/story references; migration rules stated for the whole team; KAN-124 marked as merged for current fields (acceptance pending per its report); one canonical copy of the 18/11 PO decision. The PO settled the open decisions the same day (see the 19/11 decisions in Deliverable 1); no database or permission change is implemented here.

## Entregables

1. [Diccionario consolidado](kan-107-1-diccionario-datos-consolidado.md): campos observados, decisiones PO, pendientes Fundación, grupos y finalidades.
2. [Versionado de candidatura por convocatoria](kan-107-2-versionado-formulario-por-convocatoria.md): integridad, publicación y respuestas históricas; **clasificación del curso de 15 h pendiente de PO**.
3. [Evaluación preliminar de privacidad](kan-107-3-evaluacion-privacidad.md): riesgos, acceso mínimo y fuentes oficiales.
4. [Plan de implementación](kan-107-4-plan-implementacion.md): fases de integración y **prohibición de crear migraciones desde KAN-107**.
5. [Resumen para la PO](kan-107-5-resumen-ejecutivo-po.md): decisiones, bloqueos y responsabilidades.
6. [Anexo de permisos dinámicos](kan-107-6-control-acceso-dinamico.md): autorización por categoría, rol, convocatoria y vigencia, concedible/revocable durante el proceso, **todavía no implementada**.

## Origen y trazabilidad

- [Inventario canónico de Anas (KAN-92/93)](https://github.com/EduGest-Platform/edugest-platform/blob/d59ee8cde39773af9fc041544a2346ec4ab5245d/docs/producto/diccionario-campos-candidatura.md), integrado en `dev` mediante [PR #27](https://github.com/EduGest-Platform/edugest-platform/pull/27). Contraste documental: 18/11/2026, `origin/dev` `d59ee8c`. El PR #15 ya retiró su copia. KAN-92/93 conserva el inventario observado; KAN-107 añade gobierno y versionado, sin crear un segundo inventario canónico.
- [KAN-107](https://anasfady87-1789923749606.atlassian.net/browse/KAN-107) = **diseño**, [KAN-42](https://anasfady87-1789923749606.atlassian.net/browse/KAN-42) = **implementación**.
- Rama documental: `docs/KAN-107-data-governance` → `dev`.

## Decisión de migraciones (NO ejecutar todavía)

No crear ni numerar archivos Alembic aquí. La secuencia planificada por el equipo es **admisión → documentación RAG → académico → alertas**. La propietaria del backend revisará los HEADs reales y coordinará los cambios de KAN-42 con David y demás responsables. Los números de revisión **no se reservan ni inventan** a partir de estos documentos.

## Protección de datos y controles por defecto

El formulario del **bootcamp** es la referencia de inscripción del MVP; el inventario vigente describe el curso de **15 h** como formulario de una etapa con selector de curso/fecha, mapeado a `call_id`. La captura anterior de contacto es evidencia histórica insuficiente: **decisión PO 19/11:** cada fecha concreta crea candidatura y las opciones «organizar curso» / «avísame» crean solicitud de contacto ([decisiones del 19/11](kan-107-1-diccionario-datos-consolidado.md#decisiones-po-del-19112026--po-decisions-of-19112026)). Se mantienen ciertos campos como diseño sintético por decisión funcional PO, **sin afirmar un requisito contractual del financiador ni autorizar cuotas/prioridades**.

Administración y selección: acceso por defecto dentro del ámbito autorizado. Otros perfiles: permiso base más concesión G3/G6 vigente por usuario y convocatoria, concedida/revocada por administración y auditada. Solo detalle, nunca listas ni logs. Decisión PO 19/11; no implementada.

Quedan **pendientes de la Fundación** antes de tratar datos reales: identificación y competencias del responsable, base jurídica y condición art. 9 si procede, información art. 13, plazos de retención, derechos de rectificación/supresión, justificación de eventuales criterios de selección y análisis de necesidad de EIPD. No asumir que la designación formal de DPO sea obligatoria en cualquier supuesto.

### English review note

KAN-107 is design-only. The bootcamp is the MVP intake reference. The PO settled B routing on 19 November: concrete course/date → application; organise/notify → contact request. Admin and selection have default access within their authorised scope. Other profiles need the base permission plus an active user/call/group grant managed by admin and audited. Detail only, never lists or logs. PO decision of 19 November; not implemented. Form C is outside the MVP. KAN-42 owns implementation and the shared Alembic chain. Foundation validation remains a condition for real-data use.

### Edición en español / Spanish edition note

Los documentos 1–6 son canónicos en español y cada uno incluye ahora una sección **English edition** con las secciones equivalentes (resumen fiel de decisiones, pendientes y límites, no una traducción palabra por palabra), conforme a la Constitución («secciones emparejadas dentro de un archivo»). Si hay discrepancia, prevalece la versión en español de las tablas y la decisión funcional aprobada.

### English edition (index)

KAN-107 V2 documents (design only; KAN-107 design, documentation branch `docs/KAN-107-data-governance` into `dev`): (1) consolidated data dictionary incl. field-by-field observed-vs-decided obligations; (2) per-call form versioning incl. version-change-during-filling rule; (3) preliminary privacy assessment; (4) implementation plan; (5) PO summary; (6) dynamic scoped access annex. Canonical observed inventory: `docs/producto/diccionario-campos-candidatura.md`, merged by PR #27, checked at `origin/dev` `d59ee8c` on 18/11/2026; PR #15 removed its copy. KAN-107 adds governance without duplicating that inventory. Each document 1–6 ends with an "English edition" section.

## Reconciliación técnica final / Final technical reconciliation — 19/11/2026

En `dev@c59d201` (19/11/2026), la cadena integrada es `0001 → 0003 → 0004 → 0006 → 0007 → 0005`, cabeza única `0005`. KAN-128, KAN-135, KAN-183 y KAN-153 están integrados. No existe `0002`; Alembic sigue `down_revision`, no el orden numérico. Asistencia y alertas aún no tienen migraciones integradas. / At this pinned dev snapshot the single head is `0005`; no academic or alert migration is integrated.

ES: Las decisiones del 19/11 son la referencia vigente en ambos idiomas; se han retirado contradicciones sobre edad, canal, ventana de gracia y acceso G3/G6. Las nuevas decisiones de acceso/tablero de la PO (19/11, rama `ccr-e218aef4-6l29zo@cb62c93`) amplían coordinación y eliminan acceso del aspirante; su implementación y la matriz completa pertenecen a las tareas de acceso/tablero, no a este PR documental.

EN: The 19 November decisions govern both language sections. The subsequent access/board decisions widen coordination and remove applicant access; implementing and testing that permission matrix belongs to the access/board tickets, outside this documentation PR. This package grants no live permission.
