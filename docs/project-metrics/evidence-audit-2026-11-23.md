# Auditoría de evidencia — EduGest
**Corte:** 23/11/2026 (Europe/Madrid)  
**Repositorio:** `EduGest-Platform/edugest-platform`  
**Jira:** proyecto `KAN`  
**Rama del informe:** `docs/project-metrics-dashboard`  
**Estado del informe:** auditoría focalizada; no equivale a certificación de release.

## 1. Objetivo y criterio

Contrastar el estado administrativo de Jira con evidencia técnica verificable en GitHub. Se distinguen cuatro niveles:

1. **Código integrado:** PR fusionada en `dev`.
2. **Validación técnica:** workflow/checks observados en el SHA del PR.
3. **Validación funcional/operativa:** pruebas de navegador, smoke, staging o despliegue ejecutados y documentados.
4. **Aceptación:** revisión cruzada y aceptación explícita del criterio en Jira por la persona responsable/PO.

Una PR fusionada o un check verde no demuestran por sí solos aceptación funcional completa. No se infiere que un test se ejecutó en staging si solo existe una prueba local o sintética.

## 2. Alcance y límites de la consulta Jira

Consulta ejecutada:

`project = KAN AND updated >= -14d ORDER BY updated DESC`

- Jira informa **256 incidencias** en la población consultada.
- Se inspeccionó la primera página de **100 incidencias**, todas etiquetadas `pf2-v41`.
- Distribución de estado de esa primera página: **38 Finalizada, 25 Pruebas, 30 En curso y 7 Idea**.
- Estos porcentajes/conteos son únicamente de la primera página; **no** deben extrapolarse a las 256 incidencias ni presentarse como avance global.
- La auditoría técnica detallada de este corte cubre PR **#113–#122** y las tareas Jira directamente asociadas. No constituye todavía un muestreo completo de todas las 256 incidencias.

## 3. Evidencia técnica por PR

| PR | Jira relacionado | Estado GitHub | Checks observados en el SHA | Evidencia y límites | Dictamen |
|---|---|---|---|---|---|
| [#113](https://github.com/EduGest-Platform/edugest-platform/pull/113) | KAN-125 | Fusionada | CI: success; F1 registration E2E: success | Estados de carga/error/catálogo vacío y reintento preservando el formulario. | Integrada y checks verdes; conservar KAN-125 en Pruebas hasta aceptación funcional. |
| [#114](https://github.com/EduGest-Platform/edugest-platform/pull/114) | KAN-253 | Fusionada | CI: success; F1 registration E2E: success | Regresión de accesibilidad del diálogo con datos sintéticos. | Evidencia técnica positiva; no demuestra por sí sola auditoría completa de contraste, errores y lector de pantalla. |
| [#115](https://github.com/EduGest-Platform/edugest-platform/pull/115) | KAN-134 | Fusionada | CI: success; F1 registration E2E: success | Filtro por agente y contador en timeline CRM. El filtro por vencimiento se declara fuera del PR. | Parcial respecto al título de Jira; KAN-134 permanece En curso. |
| [#116](https://github.com/EduGest-Platform/edugest-platform/pull/116) | KAN-125 | Fusionada | CI: success; F1 registration E2E: success | Prueba de navegador del fallo y recuperación del catálogo. | Refuerza #113; falta aceptación de la tarea. |
| [#117](https://github.com/EduGest-Platform/edugest-platform/pull/117) | KAN-212 | Abierta | CI: success; F1 registration E2E: success | Pruebas locales de serialización/credenciales, Ruff y Bash; smoke completo/Docker no ejecutado y no hubo despliegue. | No fusionar/cerrar Jira como completada hasta revisión cruzada y smoke acordado. |
| [#118](https://github.com/EduGest-Platform/edugest-platform/pull/118) | KAN-220 | Abierta | CI: success | Inspección de fuentes, enlaces, diff y 5 tests Vitest; no hubo ensayo de navegador, operación de BD ni despliegue. | Documentación con CI verde, pero pendiente revisión de Anas y validación operativa/aceptación. |
| [#119](https://github.com/EduGest-Platform/edugest-platform/pull/119) | Métricas de proyecto | Cerrada sin merge | No se considera evidencia de integración | El propio PR exige secretos Jira de solo lectura y una primera ejecución live contrastada antes de canonizar el snapshot. | No contar como funcionalidad integrada ni como dashboard automático disponible. |
| [#120](https://github.com/EduGest-Platform/edugest-platform/pull/120) | KAN-60 | Fusionada | CI: success; F1 registration E2E: success | Ingesta limitada a materiales compartidos por docente; tests de corpus/ingesta/embeddings, Ruff y banco de preguntas declarados PASS. | Evidencia sólida de regla de corpus integrada; falta comprobar el flujo de extremo a extremo en entorno objetivo. |
| [#121](https://github.com/EduGest-Platform/edugest-platform/pull/121) | Seguimientos de PR #97; sin ticket nuevo | Abierta | F1 registration E2E: success; **CI: failure** | Revisión de seguridad documenta un hallazgo medio corregido y uno bajo pendiente: confirmar en staging cuántos saltos añade Render. | **Bloqueada por CI fallido** y validación real de proxy pendiente. No aprobar/mergear hasta corregir y repetir checks. |
| [#122](https://github.com/EduGest-Platform/edugest-platform/pull/122) | KAN-130, KAN-151 y KAN-60 | Fusionada | CI: success; F1 registration E2E: success | Endpoint RAG con cita/abstención y ámbito previo a recuperación. Banco de 24 preguntas: keyword 17/24; híbrido 22/24; 0 respuestas erróneas, 0 fugas y 0 obsoletos en la medición declarada. Vectores desactivados en staging; el modo generado y la UI quedan fuera. | Integración técnica positiva; no equivale a aceptación del RAG completo ni habilita activar vectores en producción. |

**Resumen PR #113–#122:** 6 fusionadas, 3 abiertas y 1 cerrada sin merge. De las 9 PR con workflows revisados, 8 tienen CI verde y una (#121) CI fallido. #118 no muestra workflow F1 E2E en el SHA consultado; no debe describirse como prueba de navegador.

## 4. Estado Jira contrastado

| Tarea | Estado observado en Jira | Evidencia relacionada | Evaluación |
|---|---|---|---|
| [KAN-125](https://anasfady87-1789923749606.atlassian.net/browse/KAN-125) | Pruebas | #113 y #116 fusionadas; CI y E2E verdes | Mantener en Pruebas hasta aceptación del flujo de carga, error, vacío y reintento. |
| [KAN-253](https://anasfady87-1789923749606.atlassian.net/browse/KAN-253) | En curso | #114 fusionada; CI y E2E verdes | La regresión de referencias accesibles está cubierta; el alcance de auditoría restante necesita evidencia explícita. |
| [KAN-134](https://anasfady87-1789923749606.atlassian.net/browse/KAN-134) | En curso | #115 fusionada; filtro por agente implementado | No cerrar: el filtro por vencimiento sigue fuera del PR. |
| [KAN-60](https://anasfady87-1789923749606.atlassian.net/browse/KAN-60) | En curso | #120 y #122 fusionadas; CI verde | Mantener abierta por límites declarados: staging en keyword-only, modo generado/UI y aceptación global pendientes. |
| [KAN-212](https://anasfady87-1789923749606.atlassian.net/browse/KAN-212) | En curso | #117 abierta; CI/E2E verdes | Requiere revisión de Anas y smoke Docker/local acordado; no hubo despliegue. |
| [KAN-220](https://anasfady87-1789923749606.atlassian.net/browse/KAN-220) | En curso | #118 abierta; CI verde | Requiere revisión de Anas, aclarar discrepancia de responsable descrita en Jira/PR y aceptación de manuales. |
| [KAN-142](https://anasfady87-1789923749606.atlassian.net/browse/KAN-142) | Pruebas | Spike/documentación de hosting | No se encontró evidencia suficiente en PR #113–#122 para cerrar la decisión de hosting; requiere decisión PO y medición/contraste de límites. |
| [KAN-209](https://anasfady87-1789923749606.atlassian.net/browse/KAN-209) | Pruebas | Inventario documental y peticiones de evidencia | Aprobación documental no equivale a política de retención aceptada ni a pruebas de exportación/purga. |
| [KAN-184](https://anasfady87-1789923749606.atlassian.net/browse/KAN-184) | Pruebas | PR #92 fusionada, revisión parcial registrada | Falta revisión cruzada y confirmación de alcance de alertas frente a acciones automáticas. |
| [KAN-219](https://anasfady87-1789923749606.atlassian.net/browse/KAN-219) | En curso | PRs de CI y evidencia previas | Falta verificar/configurar checks requeridos de rama; un workflow verde no demuestra por sí solo que esté protegido como requisito. |

## 5. Hallazgos prioritarios

### Bloqueantes
1. **PR #121:** CI fallido. Corregir el fallo y repetir CI completo. La validación de `X-Forwarded-For` con los saltos reales del proxy de staging sigue pendiente.
2. **PR #117/#118:** ambas siguen abiertas. Los checks verdes no sustituyen la revisión solicitada ni las pruebas operativas expresamente no ejecutadas.
3. **KAN-134:** el filtro por vencimiento no está cubierto por #115; no cerrar la tarea como si el alcance completo estuviera entregado.

### Riesgos de evidencia/aceptación
1. No mezclar “fusionada”, “checks verdes”, “probado en staging” y “aceptado por PO”: son hitos distintos.
2. El dashboard/métricas no debe considerarse canónico: #119 se cerró sin merge y la primera ejecución live/conciliación con Jira no se ha acreditado aquí.
3. Para RAG, el resultado 22/24 es una medición del banco sintético declarado; el propio PR documenta vectores desactivados en staging y funciones posteriores fuera de alcance.
4. La muestra Jira de 100/256 no permite calcular el avance total del proyecto ni validar porcentajes globales.

## 6. Evidencia que falta recopilar

- Captura/enlace de ejecución de navegador o vídeo de aceptación para los flujos #113/#116 y #114, asociado al criterio Jira.
- Revisión explícita de Anas en #117 y #118, y resultado del smoke local/Docker acordado para #117.
- Resultado de CI corregido para #121 y evidencia de prueba de proxy en staging con configuración de saltos confirmada.
- Evidencia de aceptación PO/QA por tarea: persona, fecha, criterio aceptado y enlace a la prueba.
- Segunda/tercera página de Jira y mapeo PR↔KAN para las 256 incidencias, antes de emitir una auditoría global o porcentaje total.
- Reconciliación del dashboard con el recuento completo de Jira y reglas de denominador documentadas.

## 7. Recomendación de control

Mantener los estados Jira actuales de las tareas de esta muestra; no promover a Finalizada ninguna basándose solo en merge o CI. Priorizar #121 como bloqueo técnico, después revisión cruzada de #117/#118 y aceptación de KAN-125/KAN-253/KAN-134. La siguiente iteración debe completar la paginación de Jira y adjuntar evidencia de aceptación para convertir esta auditoría focalizada en una auditoría global.

---
**Trazabilidad:** datos consultados en Jira y GitHub el 23/11/2026. Los resultados de workflow se refieren a los SHA de cabeza de las PR consultadas; los resultados históricos o posteriores pueden cambiar. Los resultados descritos como “declarados en el PR” son afirmaciones de sus autores, no una reproducción independiente de cada ensayo.
