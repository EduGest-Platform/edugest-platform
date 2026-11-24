# KAN-217 — Disposable backup/restore rehearsal / Ensayo desechable de backup y restauración

## ES

Yohanna; único revisor solicitado: Anas. **Deadline 04/12/2026**. Base independiente `dev@f4888cc`, 24/11. La parte de despliegue/backup operativo de la tarea sigue pendiente; este incremento ensaya recuperación sobre datos sintéticos, no toca staging ni da autorización de despliegue.

### Qué hace CI

Después de pytest, el job API pasa a `scripts/ci/backup_restore.py` el ID de su servicio PostgreSQL desechable. El helper exige GitHub Actions, entorno local y marcador explícito; acepta solo un ID de contenedor hexadecimal, no URL de una base externa.

1. Crea dos bases de nombre fijo, distintas de `gistar_test`; si ya existen, falla sin reutilizarlas ni borrarlas.
2. En la primera aplica las migraciones y carga el seed desde cero. Un login sintético real crea una fila de auditoría para comprobar posteriormente su protección.
3. Calcula recuentos y SHA-256 de las filas ordenadas de cada tabla pública. Los cuerpos se procesan en memoria, sin imprimirlos; exige al menos cien candidaturas y auditoría no vacía.
4. Usa `pg_dump` en formato custom en un archivo temporal y `pg_restore --exit-on-error` en la segunda base, sin ownership/ACL heredados.
5. Compara todas las tablas por recuento **y contenido**, de modo que una alteración que conserve número de filas también falla.
6. Intenta un UPDATE de auditoría en la copia desechable: debe fallar con el mensaje del trigger append-only restaurado. Repite la comparación para comprobar que no hubo cambios.
7. Limpia exclusivamente las bases que este proceso llegó a crear y el archivo temporal. Un fallo de limpieza hace fallar el resultado. No modifica ni resetea la BD del resto de tests.

El único artefacto publicado es `synthetic-backup-summary-<SHA>`, con estado, recuentos/huellas y resultado de limpieza, retenido siete días. No contiene dump, filas, credenciales, tokens ni mensajes de error crudos. No es anonimización general ni prueba de restauración de producción: el contexto admitido es sintético y desechable. La salida de subcomandos se captura y no se vuelca a logs.

### Límites y aceptación

- No es un comando para usar contra una base compartida ni un mecanismo de backup de Render. No acepta credenciales o direcciones de producción.
- No restablece secretos, roles externos, proxies, archivos subidos ni dependencias de un proveedor. El diseño operativo de recuperación requiere responsables y aceptación aparte.
- No vuelve a generar el seed sobre la copia restaurada: eso no es necesario para comprobar fidelidad del dump y evita solapar el follow-up #121 de determinismo del seed.
- El éxito del restore prueba esta instantánea, versión de PostgreSQL y permisos de CI; no es garantía de portabilidad, RPO/RTO ni política de retención aprobada.

### Verificación realizada

Local: **13 pruebas** del directorio `scripts/ci/tests` correctas (cinco nuevas y ocho existentes). Las nuevas cubren minimización de metadata, alteración con igual número de filas, gates, quoting SQL y que nunca se borre una base cuya creación falló. Ruff, compilación Python, YAML y diff correctos. No se ejecutó Docker/PostgreSQL/backup/restore localmente y no se comprueba la finalización de CI por indicación del usuario. No se cambia Jira.

## EN

Owner Yohanna; sole requested reviewer Anas. **Deadline 2026-12-04**, independent `dev@f4888cc` snapshot on November 24. This rehearses synthetic recovery only; deployment and operational backup acceptance remain pending.

After API pytest, the CI-only helper receives its disposable PostgreSQL service container ID. Explicit GitHub/local/disposable markers and a hexadecimal container ID are required; no external DB URL is accepted. It creates two fixed probe databases distinct from the test DB, migrates/seeds the first and performs a real synthetic login for non-empty audit evidence. Existing databases cause failure and are never reused/deleted by cleanup.

A custom-format dump is restored with error checking into the second database. Every public table's sorted row count and SHA-256 content fingerprint must match. A rejected audit UPDATE must produce the restored append-only trigger's message and leave fingerprints unchanged. Only databases successfully created by this invocation are dropped, and cleanup failure fails the result. Temporary dumps and captured command output are never uploaded/logged.

The seven-day artifact holds only status, counts/digests and cleanup/audit-check flags. It is not a production backup, anonymization guarantee, provider recovery plan, secret restore, RPO/RTO promise or retention approval. The restored seed is not regenerated; pending seed-determinism follow-up #121 is separate.

Local: 13 helper tests passed, including five new privacy/corruption/context/SQL-quoting/cleanup regressions. Ruff, Python compilation, YAML and diff checks passed. Docker/PostgreSQL round-trip was not run locally, and CI completion is deliberately not checked. No Jira status, shared database or deployment change.
