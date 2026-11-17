# docs/producto — EduGest / Gistar (KAN-107 revisión V2)

**Estado:** documentos de diseño para revisión PO + Anas, sin cambios de código, OpenAPI, PostgreSQL, Jira ni GitHub. Solo datos sintéticos.

## Entregables

1. [Diccionario consolidado](kan-107-1-diccionario-datos-consolidado.md): campos observados, decisiones PO, pendientes Fundación, grupos y finalidades.
2. [Versionado de candidatura por convocatoria](kan-107-2-versionado-formulario-por-convocatoria.md): integridad, publicación y respuestas históricas; **contacto 15 h es otro flujo**.
3. [Evaluación preliminar de privacidad](kan-107-3-evaluacion-privacidad.md): riesgos, acceso mínimo y fuentes oficiales.
4. [Plan de implementación](kan-107-4-plan-implementacion.md): fases de integración y **prohibición de crear migraciones desde KAN-107**.
5. [Resumen para la PO](kan-107-5-resumen-ejecutivo-po.md): decisiones, bloqueos y responsabilidades.
6. [Anexo de permisos dinámicos](kan-107-6-control-acceso-dinamico.md): autorización por categoría, rol, convocatoria y vigencia, concedible/revocable durante el proceso, **todavía no implementada**.

## Origen y trazabilidad

- [Inventario de Anas (KAN-92/93), en PR #15](https://github.com/EduGest-Platform/edugest-platform/pull/15) — su documento `diccionario-campos-candidatura.md` sigue en una rama diferente de `dev` al momento de esta revisión. No duplicar ni fusionar automáticamente.
- [KAN-107](https://anasfady87-1789923749606.atlassian.net/browse/KAN-107) = **diseño**, [KAN-42](https://anasfady87-1789923749606.atlassian.net/browse/KAN-42) = **implementación**.
- La rama documental mencionada en el borrador original **no está verificada en GitHub**. Este paquete local no es un PR.

## Decisión de migraciones (NO ejecutar todavía)

No crear ni numerar archivos Alembic aquí. La secuencia planificada por el equipo es **admisión → documentación RAG → académico → alertas**. La propietaria del backend revisará los HEADs reales y coordinará los cambios de KAN-42 con David y demás responsables. Los números de revisión **no se reservan ni inventan** a partir de estos documentos.

## Protección de datos y controles por defecto

El formulario del **bootcamp** es la referencia de inscripción del MVP; el curso de **15 h** muestra una **solicitud de contacto** con finalidad y flujo distintos. Se mantienen ciertos campos como diseño sintético por decisión funcional PO, **sin afirmar un requisito contractual del financiador ni autorizar cuotas/prioridades**.

G3 (origen/género) y G6 (situación personal) requieren permiso base **más** concesión explícita limitada por usuario, convocatoria, categoría y duración. La gestión dinámica de esas concesiones **no existe en la API actual**. Los roles actuales ya tienen ámbito, pero no lectura granular por grupo. No mostrar G3/G6 a todo usuario con `applications.read` ni a todo administrador por defecto.

Quedan **pendientes de la Fundación** antes de tratar datos reales: identificación y competencias del responsable, base jurídica y condición art. 9 si procede, información art. 13, plazos de retención, derechos de rectificación/supresión, justificación de eventuales criterios de selección y análisis de necesidad de EIPD. No asumir que la designación formal de DPO sea obligatoria en cualquier supuesto.

### English review note

KAN-107 is design-only. The MVP application intake is modelled after the bootcamp registration form; the 15-hour course's contact form is a separate lead process. Protected groups G3/G6 require an additional, explicit, time-limited grant **and** an existing role/scope. Access may change during an active call, but no permission-management interface is implemented yet. Any future database change is owned by backend under KAN-42; never produce independent or pre-numbered Alembic revisions from these documents. Legal requirements and actual funder selection rules must be confirmed by the Foundation before real data processing.
