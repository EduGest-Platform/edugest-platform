# Métricas vivas de EduGest (Jira + GitHub)

## Qué genera

El workflow `Project metrics snapshot` consulta Jira en modo lectura y GitHub:
- Subtareas del proyecto `KAN` con etiqueta `pf2-v41`.
- Estados y distribución por etiquetas de sprint `v41-s*`.
- Subtareas sin etiqueta de sprint.
- PR abiertas con destino `dev`.
- Último resultado por workflow en la rama `dev`.

Produce `index.html`, `metrics.json` y `summary.md` como artefacto descargable de cada ejecución. Se ejecuta cada seis horas y manualmente desde Actions. No escribe en Jira, no modifica ramas y no aprueba ni fusiona PR.

## Configuración necesaria

En **Settings → Secrets and variables → Actions**, añadir estos repository secrets:

- `JIRA_BASE_URL`: URL del sitio Atlassian, por ejemplo `https://tu-organizacion.atlassian.net`.
- `JIRA_EMAIL`: correo de la cuenta técnica de solo lectura.
- `JIRA_API_TOKEN`: token API de esa cuenta.

El token debe pertenecer a una cuenta con permiso de lectura del proyecto KAN. No usar credenciales personales de escritura. GitHub usa el token efímero `github.token` con permisos de lectura declarados en el workflow.

## Cómo consultar el dashboard

1. Abrir **Actions → Project metrics snapshot**.
2. Ejecutar **Run workflow** para generar el primer corte.
3. Abrir la ejecución completada y descargar el artefacto `edugest-project-metrics-N`.
4. Abrir `index.html` localmente o consultar `summary.md` en el resumen de la ejecución.

## Definiciones y límites

- El porcentaje administrativo es subtareas Jira en estado exactamente `Finalizada` dividido por subtareas del alcance que tienen etiqueta de sprint. Las que no tienen sprint se muestran por separado.
- La etiqueta de sprint se identifica por prefijo `v41-s`; si una subtarea tiene más de una, se usa la primera alfabéticamente y debe corregirse la asignación en Jira.
- Las PR abiertas no cuentan como integradas.
- CI/E2E en verde son evidencias de validación automatizada, no prueba de aceptación completa.
- **No se calcula avance técnico ponderado**: el 71,17 % histórico no es reproducible con estados Jira/PR/CI por sí solos. Para reactivarlo hace falta una rúbrica de aceptación por sprint, con criterios y evidencias revisables.
- Los datos del informe son una instantánea del momento de ejecución, no un panel en streaming.

## Solución de problemas

Si falla la consulta Jira, revisar URL, email, token, permisos del proyecto y que el sitio admita Jira REST API v3. El workflow falla deliberadamente en vez de publicar cifras parciales.
