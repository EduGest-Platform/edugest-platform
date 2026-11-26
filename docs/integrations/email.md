# Integración de correo electrónico

KAN-277: implementación inicial de notificaciones académicas individuales por matrícula activa, con permisos por cohorte, plantillas, outbox persistente, idempotencia, auditoría y worker SMTP. Los reintentos se limitan a fallos transitorios anteriores al envío; los resultados inciertos no se reenvían automáticamente.

## Configuración local

La integración está desactivada por defecto. La API y el worker comparten las variables GISTAR_EMAIL_ENABLED, GISTAR_EMAIL_SMTP_HOST, GISTAR_EMAIL_SMTP_PORT, GISTAR_EMAIL_SMTP_SECURITY, GISTAR_EMAIL_SMTP_USERNAME, GISTAR_EMAIL_SMTP_PASSWORD, GISTAR_EMAIL_FROM_ADDRESS y GISTAR_EMAIL_TIMEOUT_SECONDS.

Para una prueba autorizada con transporte SMTP de captura y datos sintéticos, configurar estas variables en infra/.env (no versionado) y ejecutar:

```sh
docker compose -f infra/compose.yaml --profile email up --build
```

No habilitar envíos reales hasta aprobar proveedor, credenciales, destinatarios y políticas de privacidad. No guardar secretos en Git.

## Pendientes

Invitaciones Zoom (KAN-276), recordatorios automáticos, comunicaciones masivas, borradores IA revisables, preferencias y bajas, política de retención y validación operativa con proveedor institucional.
