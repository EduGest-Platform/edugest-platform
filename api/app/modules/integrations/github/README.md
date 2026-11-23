# Consumer error codes / Códigos de error del consumidor

## ES

Las excepciones públicas exponen `error.code` estable para que el futuro router
permita al frontend traducir el mensaje sin analizar textos en inglés:

| Excepción / Exception | `code` |
|---|---|
| `InvalidGithubUrl` | `invalid_url` |
| `GithubRedirected` | `redirected` |
| `GithubNotFound` | `not_found` |
| `GithubRateLimited` | `rate_limited` |
| `GithubAuthError` | `auth_error` |
| `GithubUnavailable` | `unavailable` |
| `GithubConflict` | `conflict` |
| `GithubApiError` | `api_error` |
| `GithubError` | `github_error` |

No hay router ni respuesta HTTP nueva en este PR: el adaptador y su contrato
OpenAPI se integran con `PortfolioLink`. No devolver al frontend mensajes crudos,
tokens ni destinos de redirección. El 409 de commits se convierte en cero commits.

La plantilla `.env.example` deja vacía la contraseña demo: hay que configurarla
antes de arrancar/cargar el seed. Esto no elimina el valor por defecto en
`core/config.py`; ese endurecimiento de KAN-101 corresponde al backend.

## EN

Public exceptions expose the stable `error.code` values above so the future router
can support frontend translations without parsing English exception messages.
This PR adds no HTTP route or response schema. The adapter and OpenAPI contract
will be integrated with `PortfolioLink`. Do not expose raw error messages, tokens
or redirect destinations. A commits-endpoint 409 is handled as zero commits.

The demo password in `.env.example` is empty and must be configured before startup
or seeding. This does not remove the fallback in `core/config.py`; backend
hardening remains part of KAN-101.

## Scope and future work / Alcance y trabajo futuro

See the [verified scope, offline test procedure and proposed backlog](../../../../../docs/reports/KAN-238-248-portfolio-scope.md). / Consultar el alcance comprobado, la prueba offline y los límites propuestos en ese informe.
