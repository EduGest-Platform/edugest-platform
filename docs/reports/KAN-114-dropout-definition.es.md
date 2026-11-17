# KAN-114 — Objetivo de abandono y definición de variables

Documento canónico y tablas completas: [versión inglesa](KAN-114-dropout-definition.md). Los nombres de variables y contratos no se traducen.

## Fecha y estado

**Deadline: 16/11/2026**, confirmado en el campo de vencimiento de Jira. La descripción conserva una fecha propuesta del 17/11; no se modifica ninguna de ellas ni se afirma entrega en plazo. Elaborado el 17/11/2026 sobre `dev` `6afd140feb948b570ed710b8a666e84abc58dbed`, contrastado con foundation `441772b5421a44d9f1733c6a738f4f844aba60b3`.

Responsable: Abdur; revisión: David; contratos y aceptación: Elizabeth. Estado **PROPOSED**, pendiente de aprobación. Es una especificación revisable, no un modelo entrenado ni evidencia de una reunión celebrada.

## Objetivo y etiqueta propuestos

Clasificación binaria de baja voluntaria confirmada por una persona autorizada durante los 14 días posteriores al corte, solo para matrículas activas. Es una aproximación operativa pendiente de validar, no una definición completa acordada de abandono. Ventana retrospectiva de 14 días, limitada al inicio real de matrícula; ejecución semanal propuesta. UTC para instantes y zona de cohorte para fechas lectivas. Las variables solo usan hechos ocurridos y registrados antes o en el corte.

- `1`: baja voluntaria confirmada con motivo auditable en `(corte, corte + 14 días]`.
- `0`: seguimiento completo hasta el horizonte, sin baja ni evento competidor de finalización/traslado.
- `null`: seguimiento incompleto, motivos o fechas desconocidos/disputados, finalización o traslado antes del horizonte; se excluye del entrenamiento supervisado.
- Una baja ya ocurrida al corte queda fuera de la población activa. Ausencia, silencio, retraso o alerta nunca bastan para etiquetar abandono.

El estado mutable `Enrollment.estado` no tiene fecha/motivo de baja: no permite construir por sí solo una etiqueta futura. Es necesario historial auditable y reconstrucción del estado al corte. Un registro de resultado tardío puede etiquetar retrospectivamente después del seguimiento, pero nunca convertirse en variable predictora histórica.

## Variables y disponibilidad

La tabla canónica distingue exposición, ausencia injustificada, justificada y sin dato; tasas con denominador explícito; señal ilustrativa 3/6; cobertura de competencias y último nivel publicado 1–3, con indicadores de datos ausentes. Media jornada vale 0,5 y día completo 1. Denominador cero produce desconocido. Competencias dinámicas por bootcamp/cohorte, sin columnas C1–C10 fijas; falta de evaluación no es nivel 0. Versiones de rúbrica solo se comparan si son compatibles.

Actualmente el backend tiene Enrollment, pero no las tablas académicas EDU-02/EDU-04. `created_at` es fecha de creación del registro, no necesariamente incorporación al curso. Las estructuras de `src/gistar/` son demo local. La regla `applyAbsenceRule` cuenta al menos 3 ausencias entre las últimas 6 sesiones registradas, excluyendo pendientes: no equivale a días ausentes ni debe cambiarse silenciosamente al introducir medias jornadas. Las entregas se aplazan hasta acordar Activity/Submission.

Identificadores solo para unir, autorizar y dividir datos; no entran al estimador. Se excluyen datos personales, atributos sensibles, notas crudas, estado final, decisiones futuras, alertas y variables derivadas de la etiqueta. Solo datos sintéticos.

## Evaluación posterior

Abdur prepara generador longitudinal reproducible con semilla y versión. El resultado sintético debe documentarse independientemente de la regla de ausencia; no entrenar y evaluar una tautología. Comparar DummyClassifier y LogisticRegression, imputación/escalado solo en entrenamiento y señales de datos ausentes. Mantener todas las matrículas/cortes de una misma persona en una partición; particiones temporales con separación del horizonte. Reservar cohortes si hay suficientes grupos o declarar la limitación.

Publicar prevalencia, soporte, matriz de confusión, precisión, recall, F1, PR-AUC y calibración/Brier cuando existan; declarar métricas indefinidas y particiones con una sola clase. Umbral de alerta elegido solo en validación según capacidad de revisión docente. Las métricas sintéticas no prueban validez real ni equidad. Ninguna alerta cambia matrícula, excluye o sanciona.

## Casos de aceptación y bloqueos

La versión canónica enumera ocho escenarios futuros: suma 0,5/1 y justificación separada; ausencia de registros; exclusión de información futura; límites del horizonte y censura; separación por persona/tiempo; versiones y evaluaciones ausentes; señal 3/6 sin etiquetar automáticamente; permisos docente/cohorte con 403 fuera de ámbito. Son pruebas por implementar, no resultados ejecutados.

Pendiente de Abdur y Elizabeth: aprobar etiqueta, ventanas, cadencia, política de datos insuficientes/abstención y umbral de apoyo. Elizabeth confirma inicio real, historial de baja y campos EDU-02/04. Anas ayuda a contrastar la regla local; David revisa metodología y fugas. La revisión cruzada y estas decisiones son necesarias antes de cerrar KAN-114. Este PR no cambia responsables, Jira, base de datos ni despliegues.
