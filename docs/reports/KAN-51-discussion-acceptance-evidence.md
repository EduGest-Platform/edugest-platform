# KAN-51 — Evidencia de comentarios / Discussion acceptance evidence

27/11/2026 · Elizabeth · Reviewer Yohanna · Inspected dev after #271 (merge 6002007). Static review and observed remote CI; no local execution.

## ES
| Criterio | Evidencia | Evaluación |
|---|---|---|
| Modelo único expediente/programa y respuesta al mismo hilo | #146, KAN-228 Finalizada | Implementado |
| API list/create/reply/edit/resolve y ámbito | #150–154, KAN-233 Finalizada; test_discussion_security.py | CI API PASS observado en #271; comprobar criterios negativos |
| UI expediente y estados | #217–221, KAN-235 Finalizada; paso KAN-74 Chromium | PASS remoto |
| Tablero programa, filtros y cambios concurrentes | #271; e2e/program-board-isolation.mjs | PASS remoto, manual refresh, sin realtime |
| Autor y fecha | actor_user_id y created_at; ServerDiscussions.tsx muestra Tú/Equipo | Parcial: decidir visibilidad de identidad de otros autores con PO |
| Edición/borrado lógico y auditoría | #154: rollback auditoría, versiones, autoría, no cambia admisión/matrícula | Suite API PASS; borrado lógico no implica borrado físico |
| XSS y ámbito | #154: markup como JSON y nosniff, sin texto libre en audit; renderer JSX interpola texto | XSS navegador específico no verificado; KAN-244 Pruebas |
| Menciones opcionales | No exigir notificaciones externas; no afirmar implementación | Fuera del cierre salvo aceptación PO |

Evidencia: [#146](https://github.com/EduGest-Platform/edugest-platform/pull/146), [#154](https://github.com/EduGest-Platform/edugest-platform/pull/154), [#221](https://github.com/EduGest-Platform/edugest-platform/pull/221), [#271](https://github.com/EduGest-Platform/edugest-platform/pull/271). [CI #271](https://github.com/EduGest-Platform/edugest-platform/actions/runs/46032355814): API, web, contrato y compose PASS. [F1 E2E #271](https://github.com/EduGest-Platform/edugest-platform/actions/runs/46032355812): Internal discussion keyboard and concurrent edit recovery y Program board with independent sessions PASS.

Cierre pendiente: ejecutar regresión Chromium específica con texto sintético que parezca HTML en asunto, cuerpo y respuesta; comprobar que aparece como texto sin nodos/handlers ejecutables, tras recargar y en otra sesión autorizada. Verificar 401/403/404 en ámbitos ajenos, no incluir texto libre en auditoría, editar/borrar y resolver sin modificar admisión/matrícula. Confirmar visibilidad de autor y revisión cruzada de KAN-244; no cerrar historia por CI global. No se añadieron pruebas nuevas en este PR.

## EN
The shared thread/reply model, scoped API, application UI and program board are merged. Observed #271 CI and dedicated browser steps passed. Author identity is currently rendered as You/Team; PO must decide if named authors are required. API JSON/nosniff and React text interpolation are not a browser XSS certification. KAN-244 remains in Testing until dedicated synthetic markup rendering and authorization/audit evidence are reviewed. Logical deletion is not physical erasure. No realtime or external notifications are claimed. Cross-review and PO acceptance remain mandatory.
