# docs/producto — EduGest / Gistar (KAN-107 revisión V2)

**Estado:** documentos de diseño en revisión en el [PR #24](https://github.com/EduGest-Platform/edugest-platform/pull/24) (hacia `dev`, abierto, sin fusionar), para revisión de Anas y aceptación de la PO. Sin cambios de código, OpenAPI, PostgreSQL ni migraciones. Solo datos sintéticos.


## Decisión PO del 18/11/2026 / PO decision of 18/11/2026

**ES:** aceptada la referencia del bootcamp de **1.250 h** y las recomendaciones asociadas (edad configurable, residencia Madrid obligatoria, conocimientos de programación sin experiencia profesional exigida, motivación inicial opcional y disponibilidad inicial opcional con dedicación intensiva informada). La [decisión canónica y su evidencia](kan-107-1-diccionario-datos-consolidado.md#decisión-po-aceptada-el-18112026--po-decision-accepted-on-18112026) distinguen lo aceptado de lo pendiente y del contrato aún sin modificar. Anas y aceptación final del paquete siguen pendientes.

**EN:** the PO accepted the **1,250-hour bootcamp** reference and associated recommendations: configurable age, mandatory Madrid-region residence, programming background without professional experience required, optional initial motivation and availability with intensive commitment explained. See the canonical decision/evidence above; API/DB changes are not implemented. Other open decisions, Anas review and final package acceptance remain pending.


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
- Rama documental: `docs/KAN-107-data-governance` → `dev`, en el PR #24 (abierto, pendiente de revisión).

## Decisión de migraciones (NO ejecutar todavía)

No crear ni numerar archivos Alembic aquí. La secuencia planificada por el equipo es **admisión → documentación RAG → académico → alertas**. La propietaria del backend revisará los HEADs reales y coordinará los cambios de KAN-42 con David y demás responsables. Los números de revisión **no se reservan ni inventan** a partir de estos documentos.

## Protección de datos y controles por defecto

El formulario del **bootcamp** es la referencia de inscripción del MVP; el inventario vigente describe el curso de **15 h** como formulario de una etapa con selector de curso/fecha, mapeado a `call_id`. La captura anterior de contacto es evidencia histórica insuficiente: **pendiente PO** confirmar si coexisten ambos formularios y qué opciones crean candidatura o solicitud de contacto. Se mantienen ciertos campos como diseño sintético por decisión funcional PO, **sin afirmar un requisito contractual del financiador ni autorizar cuotas/prioridades**.

G3 (origen/género) y G6 (situación personal) requieren permiso base **más** concesión explícita limitada por usuario, convocatoria, categoría y duración. La gestión dinámica de esas concesiones **no existe en la API actual**. Los roles actuales ya tienen ámbito, pero no lectura granular por grupo. No mostrar G3/G6 a todo usuario con `applications.read` ni a todo administrador por defecto.

Quedan **pendientes de la Fundación** antes de tratar datos reales: identificación y competencias del responsable, base jurídica y condición art. 9 si procede, información art. 13, plazos de retención, derechos de rectificación/supresión, justificación de eventuales criterios de selección y análisis de necesidad de EIPD. No asumir que la designación formal de DPO sea obligatoria en cualquier supuesto.

### English review note

KAN-107 is design-only. The MVP application intake is modelled after the bootcamp registration form; the current inventory describes the 15-hour form as single-stage intake with a course/date selector mapped to `call_id`. PO must settle its application/contact routing; the older contact screenshot does not establish a separate lead model. Protected groups G3/G6 require an additional, explicit, time-limited grant **and** an existing role/scope. Access may change during an active call, but no permission-management interface is implemented yet. Any future database change is owned by backend under KAN-42; never produce independent or pre-numbered Alembic revisions from these documents. Legal requirements and actual funder selection rules must be confirmed by the Foundation before real data processing.

### Edición en español / Spanish edition note

Los documentos 1–6 son canónicos en español y cada uno incluye ahora una sección **English edition** con las secciones equivalentes (resumen fiel de decisiones, pendientes y límites, no una traducción palabra por palabra), conforme a la Constitución («secciones emparejadas dentro de un archivo»). Si hay discrepancia, prevalece la versión en español de las tablas y la decisión funcional aprobada.

### English edition (index)

KAN-107 V2 documents (design only, under review in PR #24, not merged): (1) consolidated data dictionary incl. field-by-field observed-vs-decided obligations; (2) per-call form versioning incl. version-change-during-filling rule; (3) preliminary privacy assessment; (4) implementation plan; (5) PO summary; (6) dynamic scoped access annex. Canonical observed inventory: `docs/producto/diccionario-campos-candidatura.md`, merged by PR #27, checked at `origin/dev` `d59ee8c` on 18/11/2026; PR #15 removed its copy. KAN-107 adds governance without duplicating that inventory. Each document 1–6 ends with an "English edition" section.
