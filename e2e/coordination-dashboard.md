# Panel de Coordinación / Coordination dashboard

**ES** — Ejecuta el recorrido sobre una base PostgreSQL local desechable, migrada y poblada con `python -m app.seed`. Sirve la web en modo API según [los comandos del repositorio](../commands.md). Usa la contraseña sintética configurada en los dos servicios.

**EN** — Run the journey against a disposable local PostgreSQL database, migrated and populated with `python -m app.seed`. Serve the web in API mode using the [repository commands](../commands.md). Use the synthetic password configured for both services.

```sh
WEB_URL=http://127.0.0.1:8443/ GISTAR_API=http://127.0.0.1:8000 node e2e/coordination-dashboard.mjs
```

**ES** — En el seed limpio, IA 2027A contiene 50 candidaturas y 25 plazas ofertadas. El navegador comprueba 16 enviadas y 12 convocadas, una etapa con cifra oculta y otra con cero. También verifica que IA 2026B oculta todo el desglose y que Data 2027A muestra sus propias cifras. Conserva los umbrales de privacidad predeterminados.

**EN** — In the fresh seed, IA 2027A contains 50 applications and 25 offered places. The browser verifies 16 submitted, 12 invited, a hidden stage count and a zero. It also verifies that IA 2026B hides its breakdown and that Data 2027A shows its own counts. Keep the default privacy thresholds.
