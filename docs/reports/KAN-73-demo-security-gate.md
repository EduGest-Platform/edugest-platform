# KAN-73 — Demo security acceptance gate / Gate de seguridad de demo

27/11/2026 · Owner Elizabeth · Reviewer Yohanna · PROPOSED / BLOCKED on environment evidence and retention acceptance. No deployment, secrets read, credentials printed, production writes or real data.

## ES — Matriz de verificación

| Control | Evidencia de código y CI | Comprobación de entorno pendiente |
|---|---|---|
| Credenciales no predeterminadas | KAN-99/100/101, #37, Gitleaks, config.py exige contraseña no demo fuera de local | Operador confirma secretos distintos por entorno, rotación y no exposición; no copiar valores |
| TLS y proxy | render.yaml, docs/deploy/README.md, #135, HSTS solo HTTPS no local | URL HTTPS válida, redirección segura y proxy hops efectivos |
| Límites y cabeceras | #135, KAN-208; límites de sesión/intentos, no-store, nosniff | Verificar cabeceras API y configuración efectiva; rate limiting por proceso, no distribuido |
| RBAC | #38, #17, #140, #148 y KAN-214; controles de ámbito, actor, expiración | Smoke sintético por rol, acceso anónimo denegado, ámbitos ajenos y privilegio mínimo; sin probar con terceros |
| Datos sintéticos | Semilla sintética y CI entorno desechable | Confirmar dataset y cuentas de demo; no datos reales, no exportación pública |
| Retención | KAN-209 / #25 inventario, no política aplicada | Aprobar plan, registrar configuración efectiva de plataforma/Actions/BD y responsable de borrado |

### Propuesta de retención para DEMO sintética (no política legal ni aprobada)
- Logs operativos y artefactos CI: objetivo 14 días desde generación, acceso restringido a equipo autorizado. Si proveedor impone otro límite, documentar valor efectivo y excepción.
- Sesiones: TTL configurado y revocación; eliminar/resetear solo mediante procedimiento aprobado al desmantelar la demo.
- BD, auditoría, CRM y evidencias sintéticas: mantener hasta defensa y revisión final, propuesta de retirada dentro de 30 días desde cierre del proyecto. Conservar únicamente informes agregados y artefactos sin identificadores si se autoriza. No ejecutar purga ni desactivar append-only; destrucción del entorno completo requiere aprobación y verificación.
- Exportaciones/backups: deshabilitar exportaciones externas innecesarias; inventariar copias y permisos, aplicar fecha de retirada equivalente o excepción documentada. La eliminación de una copia no demuestra eliminación de todas.
- Si se detectan datos reales, bloquear demo y escalar a PO/SM; no usar este plan para datos personales reales.

### Checklist operativa reproducible (entorno autorizado)
1. Registrar fecha, entorno, SHA desplegado, propietario y revisora; verificar que el SHA corresponde al CI aprobado y sin checks obligatorios omitidos. No desplegar por este documento.
2. Confirmar configuración en panel por operador: entorno staging/production, secretos no default y distintos, CORS exacto, proxy hops, BD privada, cuentas sintéticas y mínimo privilegio. Registrar solo PASS/FAIL, no valores.
3. Desde terminal autorizada, comprobar TLS y las cabeceras con las peticiones GET de la tabla siguiente. Registrar solo estado y cabeceras enumeradas. Los controles de autenticación se ejecutan por separado en el paso 4.
4. Ejecutar smoke positivo y negativo con cuentas sintéticas: login/logout, recurso propio, otro ámbito 403/404, anónimo 401, rol no autorizado. Comprobar límites solo en entorno desechable o con aprobación explícita; no saturar staging compartido. No capturar secretos ni cuerpos con PII.
5. PO aprueba plazos, propietario y mecanismo de retirada; operador registra retención efectiva de proveedor, Actions y BD/copia con fecha, evidencia redactada y desviaciones. Validar retirada primero en entorno desechable.
6. Yohanna revisa evidencia; cualquier FAIL/NOT_RUN en control obligatorio impide cierre. Registrar aceptación explícita y enlace al artefacto sin secretos.

### Comprobación HTTP por ruta / HTTP check by route

| Petición / Request | Código y cabeceras esperados / Expected status and headers |
|---|---|
| `GET /health` | `200` si responden servicio y BD; `503` es fallo de disponibilidad. Exigir `X-Content-Type-Options: nosniff`. La política de la aplicación no exige `Cache-Control: no-store` en esta ruta. / `200` when service and database are healthy; `503` fails availability. Require `X-Content-Type-Options: nosniff`. Application policy does not require `Cache-Control: no-store` on this route. |
| `GET /api/v1/calls` | `200`, `Cache-Control: no-store` y `X-Content-Type-Options: nosniff`. El catálogo es público y no requiere token. / `200`, `Cache-Control: no-store` and `X-Content-Type-Options: nosniff`. The catalogue is public and requires no token. |

**ES** — Usar el origen HTTPS de la API autorizado. En HTTPS fuera de local, comprobar también `Strict-Transport-Security` en ambas rutas. La aplicación emite `max-age=31536000` cuando ASGI reconoce HTTPS. Si la cabecera la aplica el proxy, contrastar el valor con la política efectiva del entorno. En local no se exige HSTS. `HEAD /health` devuelve `405`; la comprobación obligatoria usa `GET`.

**EN** — Use the authorized HTTPS API origin. Outside local development, also check both routes for `Strict-Transport-Security`. The application emits `max-age=31536000` when ASGI recognizes HTTPS. If the proxy sets HSTS, compare the value with the environment policy. Local development does not require HSTS. `HEAD /health` returns `405`; the mandatory check uses `GET`.

```sh
: "${DEMO_API_ORIGIN:?Set the authorized HTTPS API origin}"
for path in /health /api/v1/calls; do
  printf '%s\n' "$path"
  headers=$(curl --silent --show-error --proto '=https' --max-time 10 \
    --output /dev/null --dump-header - "${DEMO_API_ORIGIN%/}$path") || exit 1
  printf '%s\n' "$headers" |
    awk 'tolower($0) ~ /^(http\/|cache-control:|x-content-type-options:|strict-transport-security:)/'
done
```

CI observado: [#271 CI](https://github.com/EduGest-Platform/edugest-platform/actions/runs/46032355814) PASS (API/web/secrets/compose); [F1 E2E](https://github.com/EduGest-Platform/edugest-platform/actions/runs/46032355812) PASS en entorno desechable. No son evidencia del entorno real. #135 limita throttling por proceso; #25 declara retención pendiente; todos los hijos Jira finalizados no equivalen al DoD de la historia.

## EN
The table reconciles code-level controls with the missing environment checks. The proposed synthetic-demo retention targets (14 days for operational logs/CI artifacts and removal of the synthetic environment within 30 days after project closure) are recommendations, not approved policy or legal advice. Confirm provider limits, owners, backups and deletion mechanism; never purge or disable append-only without authorization. The checklist requires deployed SHA, TLS, headers, private DB, nondefault rotated secrets, scoped synthetic accounts and negative access checks, plus documented actual retention. Local checks on disposable PostgreSQL confirmed GET and HEAD status codes and the header differences in the table. HSTS and actual deployment acceptance still require evidence from the authorized environment. The story stays open until mandatory evidence and Yohanna/PO acceptance are recorded.


## Evidence record / Registro de evidencias (template — NOT_RUN)

Complete one record per authorized environment and deployed SHA. / Completar un registro por entorno autorizado y SHA desplegado. No secrets, tokens, raw logs or personal data. / Sin secretos, tokens, logs brutos ni datos personales.

| Control / Control | Expected result / Resultado esperado | Status | Redacted evidence / Evidencia redactada | Owner / Responsable |
|---|---|---|---|---|
| Deployment identity / Identidad | Deployed SHA matches reviewed CI; synthetic environment identified | NOT_RUN | — | Operator |
| Secrets / Secretos | No defaults, rotation confirmed, no values exposed | NOT_RUN | — | Operator |
| TLS / TLS | Valid HTTPS certificate, safe HTTP redirect or explicitly approved controlled environment | NOT_RUN | — | Operator |
| Health headers / Cabeceras de salud | `GET /health`: 200, nosniff, HSTS where applicable | NOT_RUN | — | Operator |
| API headers / Cabeceras de API | `GET /api/v1/calls`: 200, no-store, nosniff, HSTS where applicable | NOT_RUN | — | Operator |
| Rate limits / Límites | Effective limits confirmed; no shared-environment load test | NOT_RUN | — | Operator + QA |
| Access / Acceso | Authorized request succeeds; anonymous 401, forbidden/out-of-scope 403 or 404; no disclosure | NOT_RUN | — | QA |
| Synthetic data / Datos sintéticos | Synthetic fixtures only, least-privilege demo roles | NOT_RUN | — | Operator + QA |
| Retention / Retención | Effective provider, CI, database and backup periods recorded; owner and removal date approved | NOT_RUN | — | PO + Operator |

Record date/time, SHA, environment, reviewer, result and evidence URL. Mark exceptions separately with owner, mitigation and explicit approval; an exception does not turn NOT_RUN into PASS. / Registrar fecha/hora, SHA, entorno, revisión, resultado y enlace. Las excepciones requieren responsable, mitigación y aprobación expresa; no convierten NOT_RUN en PASS.

**Gate decision / Decisión de gate:** BLOCKED until all mandatory controls have evidence and the PO and cross-reviewer record acceptance. / BLOCKED hasta acreditar todos los controles obligatorios y registrar la aceptación PO y revisión cruzada. This template is not a certification. / Esta plantilla no es una certificación.
