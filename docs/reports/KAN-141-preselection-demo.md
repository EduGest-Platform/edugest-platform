# Guion de demo de admisión / Admissions demo script

## Preparación / Setup

**ES** — Utiliza una base PostgreSQL local desechable y datos sintéticos. Arranca EduGest en modo API con los [comandos del repositorio](../../commands.md#2-postgresql--fastapi). Usa una convocatoria de IA y otra de datos, con personal asignado a cada una. Crea una candidatura desde el catálogo de IA y conserva el identificador de la respuesta.

**EN** — Use a disposable local PostgreSQL database and synthetic data. Start EduGest in API mode using the [repository commands](../../commands.md#2-postgresql--fastapi). Use an AI call and a data call with staff assigned to each. Create one application from the AI catalogue and keep the ID returned in the response.

## Recorrido / Walkthrough

| Paso / Step | Acción / Action | Evidencia en pantalla o respuesta API / Screen or API evidence |
|---|---|---|
| 1 | ES: Desde la otra convocatoria, intenta convocar la candidatura. Repite desde la convocatoria correcta. EN: Attempt the handoff from the other call. Repeat from the correct call. | ES: `403` en la primera sesión. `201` desde la correcta. Usa otra candidatura de esa convocatoria para el resto del guion. EN: `403` in the first session and `201` from the correct one. Use another application from that call for the remaining steps. |
| 2 | ES: Configura un requisito obligatorio en la convocatoria y evalúa su versión sin una revisión previa. Registra una excepción en revisión. EN: Configure a required item for the call and evaluate its version before any review. Record an exception under review. | ES: `human_review_required: true` y etapa `enviada`. EN: `human_review_required: true` and stage `enviada`. |
| 3 | ES: Convoca desde Captación y abre el expediente desde Selección. EN: Invite from Recruitment and open the dossier from Selection. | ES: Etapa `convocada`, con una revisión pendiente registrada en la decisión humana. EN: Stage `convocada`, with one open review captured in the human decision. |
| 4 | ES: Aprueba la excepción con la versión actual y vuelve a evaluar el requisito. Consulta el historial con la cuenta de Selección. EN: Approve the exception using the current version and evaluate the requirement again. Read history from the Selection account. | ES: Dos revisiones con sus autores y motivos sintéticos. La etapa sigue en `convocada` y todavía no hay matrícula. EN: Two revisions with their authors and synthetic reasons. The stage remains `convocada` and enrollment is still absent. |
| 5 | ES: Para continuar hasta la matrícula, usa una cohorte sintética con plazas y la configuración de quórum de la prueba de admisión. Registra las dos decisiones humanas desde sesiones distintas. EN: To continue to enrollment, use a synthetic cohort with available seats and the admissions test's quorum configuration. Submit the two human votes from separate sessions. | ES: El primer voto queda pendiente. El que completa el quórum deja una sola matrícula y su vínculo con la candidatura. EN: The first vote stays pending. The vote that completes quorum produces one enrollment linked to its application. |

**ES** — El paso 5 se reproduce en una prueba independiente de admisión con su propia candidatura sintética. El guion hasta el paso 4 se reproduce en la prueba de requisitos y preselección. Usa OpenAPI para los pasos manuales que requieran ver el detalle de una respuesta. Muestra el expediente únicamente con una cuenta autorizada.

**EN** — Step 5 is reproduced in a separate admissions test using its own synthetic application. The requirement and preselection test reproduces the walkthrough through step 4. Use OpenAPI for manual steps that require inspecting the full response. Show the dossier only with an authorized account.

## Ensayo automatizado / Automated rehearsal

```sh
cd api
python -m pytest tests/test_preselection_review_journey.py tests/test_admission_outcome_journeys.py
```

**ES** — Configura antes `GISTAR_TEST_DATABASE_URL` con una base sintética desechable según los [comandos del repositorio](../../commands.md#2-postgresql--fastapi). Las pruebas reinician esa base. Guarda el resultado de pytest y el SHA ensayado.

**EN** — Set `GISTAR_TEST_DATABASE_URL` to a disposable synthetic database using the [repository commands](../../commands.md#2-postgresql--fastapi). Tests reset that database. Record the pytest result and the rehearsed SHA.
