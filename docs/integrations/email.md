# Integración de correo electrónico

KAN-277: implementación inicial de notificaciones académicas individuales por matrícula activa, con permisos por cohorte, plantillas, outbox persistente, idempotencia, auditoría y worker SMTP. Los reintentos se limitan a fallos transitorios anteriores al envío; los resultados inciertos no se reenvían automáticamente.

## Configuración local

La integración está desactivada por defecto. La API y el worker comparten las variables GISTAR_EMAIL_ENABLED, GISTAR_EMAIL_SMTP_HOST, GISTAR_EMAIL_SMTP_PORT, GISTAR_EMAIL_SMTP_SECURITY, GISTAR_EMAIL_SMTP_USERNAME, GISTAR_EMAIL_SMTP_PASSWORD, GISTAR_EMAIL_FROM_ADDRESS y GISTAR_EMAIL_TIMEOUT_SECONDS.

Para una prueba autorizada con transporte SMTP de captura y datos sintéticos, configurar estas variables en infra/.env (no versionado) y ejecutar:

```sh
docker compose -f infra/compose.yaml --profile email up --build
```

No habilitar envíos reales hasta aprobar proveedor, credenciales, destinatarios y políticas de privacidad. No guardar secretos en Git.

## Recuperación de una petición con respuesta incierta / Recovering an uncertain request

La pestaña conserva en `sessionStorage` la petición original por cuenta y cohorte (matrícula, asunto, programación y referencia). Tras un error de comunicación, la interfaz muestra esa petición y permite volver a intentarla con la misma referencia. Cambiar de cohorte, desmontar la pantalla o recargar la misma pestaña conserva la petición. Otra pestaña independiente, otro navegador o el borrado del almacenamiento pueden dejarla inaccesible.

Si se pierde esa copia, consulta el historial de la cohorte con una cuenta autorizada y escala la incidencia antes de crear otro aviso. La lista no permite identificar de forma fiable una petición incierta sin su referencia original. Un futuro mecanismo de recuperación debería buscar una operación persistida con un identificador verificable y comprobar en servidor el actor y el ámbito antes de reutilizarla. No se puede deducir la identidad de una operación a partir del asunto o de la hora.

The tab keeps the exact request and idempotency key in `sessionStorage` for the account and cohort. Reloading the same tab keeps the record; an independent tab, a different browser or cleared storage may lose access to it. Review authorised cohort history and escalate before creating another notice. A future server lookup needs a verifiable operation identifier and server-side actor and scope checks. A subject or timestamp cannot identify the request.

## Pendientes / Pending

Invitaciones Zoom (KAN-276), recordatorios automáticos, comunicaciones masivas, borradores IA revisables, preferencias y bajas, política de retención y validación operativa con proveedor institucional.
