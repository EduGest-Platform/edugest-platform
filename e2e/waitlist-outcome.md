# F2 waitlist and own enrollment / Lista de espera y matrícula propia (KAN-49)

ES — La prueba envía una candidatura sintética desde el formulario HTTP y registra dos decisiones humanas que requieren dos firmas cada una. Mientras está en lista de espera, la persona solicitante consulta su estado sin matrícula. La primera firma de promoción conserva ese resultado. La segunda aplica la admisión y la cuenta puede consultar su propia matrícula desde el endpoint académico. Otra cuenta solicitante recibe 404. Una segunda ejecución verifica que la matrícula y el historial se conservan en PostgreSQL.

EN — The test submits a synthetic application through the public HTTP form and records two human decisions requiring two signatures each. The applicant sees a waitlist outcome without an enrollment. The first promotion signature preserves that outcome. The second applies the admission and the same account can read its enrollment through the academic endpoint. Another applicant account receives 404. The second run checks that PostgreSQL preserves the same enrollment and decision history.

## Reproducir / Reproduce

Arranca el Compose desechable con el seed sintético. Exporta en tu terminal la misma contraseña sintética usada por el servicio. / Start the disposable Compose services with the synthetic seed. Export the same synthetic password used by the API in your terminal.

```sh
docker compose -f infra/compose.yaml exec -T -e GISTAR_E2E_FIXTURE=disposable-synthetic api python < e2e/prepare-f2.py
docker compose -f infra/compose.yaml exec -T -e GISTAR_E2E_FIXTURE=disposable-synthetic api python < e2e/prepare-waitlist.py
node e2e/waitlist-outcome.mjs
node e2e/waitlist-outcome.mjs
```

La fixture solo prepara una cohorte y cuentas sintéticas en el entorno desechable. Todas las transiciones y matrículas del recorrido pasan por la API. / The fixture only prepares reference data and a synthetic account in the disposable environment. The journey drives all application transitions and enrollment through the API.
