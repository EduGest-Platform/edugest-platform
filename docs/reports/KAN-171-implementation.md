# KAN-171 — Implementation / Implementación

## ES

Implementación: Yohanna. Tarea asignada a Elizabeth; único revisor solicitado: Anasfady. Deadline Jira: **26/11/2026**. Incremento del 24/11/2026.

Añade RiskAlert e Intervention y migración reversible 0013. Evidencia vinculada a matrícula, hash y versión de modelo, fecha de corte, abstención o score sintético, cuatro señales observables acotadas y responsable de revisión. Restricciones impiden etiquetar estos datos como validados para personas o ejecutar intervenciones de expulsión. No crea alertas ni cambios de matrícula automáticamente.

## EN

Implementation: Yohanna. Jira assignee: Elizabeth. Sole requested reviewer: Anasfady.

Adds RiskAlert/Intervention models and reversible migration 0013. Records enrollment-bound model hash/version, cutoff, synthetic score or abstention, four bounded observable signals and human support records. Unique observation key prevents duplicates. No routes, scoring integration or automatic learner mutations are introduced.

## Validation / Validación

PASS: two offline model/migration parity tests, PostgreSQL DDL compilation, Alembic single-head and upgrade/downgrade SQL generation, Ruff, Python compilation and diff checks. Twelve PostgreSQL persistence cases added but NOT RUN locally.

## Limits / Límites

Schema foundation only: KAN-190, KAN-203 and scoring still need scoped services, audit, role validation and human policy review. User foreign keys do not confer staff authority. Experimental support flags are not an accepted threshold. Notes must avoid sensitive data. No migration run against a real/shared DB. / Solo base de esquema; falta integración autorizada y pruebas PostgreSQL.

CI completion is not awaited, as requested. No Jira changes, merge or deployment. / No se espera al CI por petición del usuario. No se cambia Jira ni se fusiona o despliega.
