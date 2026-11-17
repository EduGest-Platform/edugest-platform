# KAN-109 — F1 RBAC regression / Regresión de permisos F1

Owner / responsable: Yohanna. Reviewer / revisión: Elizabeth; optional second security review / segunda revisión opcional: David.

## ES

La suite `api/tests/test_rbac_regression.py` amplía `test_rbac.py` sin cambiar permisos ni endpoints. Usa las fixtures existentes que migran y reinician **PostgreSQL sintético desechable**. Nunca ejecutarla sobre una base compartida o producción.

Cobertura nueva: rutas protegidas con sesión ausente/token inválido; escritura CRM cruzada sin efectos ni auditoría de éxito; suplantación mediante cabeceras/parámetros/body; agregados fuera de ámbito; revocación de rol y desactivación de cuenta durante sesión activa; autor CRM impuesto por servidor; vista propia sin notas internas ni redirección a otra persona. Incluye accesos permitidos antes de revocación y escritura autorizada como controles positivos.

Desde `api/`, con dependencias y `GISTAR_TEST_DATABASE_URL` apuntando a PostgreSQL sintético dedicado:

```sh
python -m pytest tests/test_rbac.py tests/test_rbac_regression.py -q
```

El CI existente ejecuta `pytest` en `api/` con PostgreSQL de servicio, por lo que descubre este archivo automáticamente. Validación local: sintaxis Python y diff; Docker no accesible en esta sesión, así que no se afirma pytest local correcto. El resultado de ejecución se aporta en Checks del PR. No cubre contratos futuros F2/F3, decisiones, invitaciones, alertas ni asistentes ausentes en la base; no cierra seguridad de todo el producto ni sustituye E2E/revisión humana.

## EN

`api/tests/test_rbac_regression.py` extends existing authorization tests without modifying permissions or endpoints. Existing fixtures migrate/reset **disposable synthetic PostgreSQL**; never run on shared/production databases.

New coverage: anonymous/invalid-token access, foreign CRM writes without events/success audits, forged roles/scopes in headers/query/body, foreign aggregates, live role revocation/account deactivation, server-derived CRM authors, and own-application views without internal notes or person-ID overrides. Positive controls include authorized writes and pre-revocation access.

Run the command above from `api/` with dependencies and a dedicated synthetic PostgreSQL test URL. Existing API CI discovers the file through `pytest`. Local validation covers syntax/diff only; Docker is unavailable to this session, so no local pytest pass is claimed. See PR Checks for execution evidence. Future F2/F3, decisions, invitations, alerts and assistants are outside this slice; this is neither a full security certification nor a substitute for E2E/human review.
