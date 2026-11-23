# Decisión de selección → matrícula (S2)

Estado: **IMPLEMENTADO en API, con pruebas ejecutadas**. Sin interfaz web todavía. Relacionado con KAN-48 (decisión de admisión registrada con motivo); el número de ticket y su cierre los confirma Elizabeth.
Fecha: 23/11/2026 · Base: `dev` con migración `0009` como cabeza.

**EN summary:** adds the human admission decision that ends selection (`admitida`, `lista_espera`, `no_admitida`). Admitting creates the `Enrollment` in the same transaction, so the applicant → coder path no longer depends on the seed. Append-only decision record, fixed-text CRM entry, audit without free text, role + scope checks, place limit per call. No automatic decisions and no emails are sent.

## 1. Qué añade

| Pieza | Detalle |
|---|---|
| `POST /api/v1/applications/{id}/selection-decisions` | Registra una decisión humana. Con `admitida` exige `cohort_id` y crea la matrícula (`estado = activa`, enlazada a la candidatura) |
| `GET /api/v1/applications/{id}/selection-decisions` | Historial de decisiones de la candidatura, con quién, cuándo y por qué |
| Tabla `selection_decision` (migración `0010`) | Registro de solo adición, con el mismo patrón que `preselection_decision`. Restricción en base de datos: solo una admisión lleva cohorte y matrícula |
| Permisos `selection.read` y `selection.decide` | Selección y coordinación por defecto (decisión PO 19/11, nota 3 de `roles-y-permisos-objetivo.md`); administración por el comodín. Captación, docente, coder y aspirante no los tienen |

La decisión, el cambio de etapa, la matrícula, la entrada en el CRM y el evento de auditoría se guardan en **una sola transacción**: si falla la auditoría, no queda nada a medias (hay una prueba de ello).

## 2. Reglas

| Regla | Respuesta si no se cumple |
|---|---|
| Solo se decide desde `convocada`, `evaluacion_en_curso`, `pendiente_decision_humana` o `lista_espera` | 409 `selection_not_started`, `selection_ended` o `application_withdrawn` |
| Desde la lista de espera solo se puede admitir o marcar como no admitida | 409 `already_on_waiting_list` |
| La cohorte debe pertenecer a la convocatoria de la candidatura | 422 `cohort_not_in_call`. Mismo mensaje si la cohorte no existe, para no confirmar cohortes de otras convocatorias |
| La persona no puede estar ya matriculada en esa cohorte | 409 `already_enrolled` |
| Admitidas de la convocatoria < `plazas` | 409 `no_places_left`, con el aviso de que puede quedar en lista de espera |
| Permiso y ámbito comprobados en servidor antes de leer nada más | 403 `no_scope_permission` |
| Motivo obligatorio (1 a 500 caracteres) y sin campos extra | 422 |

Las plazas se cuentan con candidaturas en etapa `admitida` de esa convocatoria. La candidatura y su convocatoria se bloquean juntas durante la decisión, de modo que dos admisiones simultáneas no pueden superar las plazas (prueba con dos peticiones concurrentes).

El texto del CRM es fijo («Selección terminada: …») y el motivo libre se queda solo en `selection_decision`: el historial que leen otros perfiles y la auditoría no lo contienen.

## 3. Qué NO hace (decisiones pendientes)

| Tema | Situación |
|---|---|
| Número de firmas | La propuesta es dos personas distintas y la fundación no la ha confirmado (nota 3 de `roles-y-permisos-objetivo.md`). Aquí basta **una** decisión humana. Al ser un registro de solo adición, una segunda firma se podrá añadir sin cambiar lo existente |
| Correos de estado | No se envía nada. «Esta vez no» exige revisión humana antes de enviarse (KAN-50) |
| Invitación al coder al matricular (D2) | No implementada. La matrícula existe, pero la invitación sigue pendiente |
| Etapas internas de selección | No hay endpoint para pasar de `convocada` a `evaluacion_en_curso` o `pendiente_decision_humana`, así que se permite decidir desde cualquiera de las tres |
| Corregir una decisión | Una candidatura `admitida` o `no_admitida` no se puede volver a decidir por la API. Hace falta una regla de corrección con motivo y permiso propio |
| Baja de matrícula | Fuera de este cambio. La baja se registra en la matrícula, no aquí |
| Cohorte de la convocatoria | Si la convocatoria no tiene cohorte asociada, hay que crearla antes de admitir. No hay endpoint para crear cohortes |
| Interfaz web | Sin cambios. La web sigue en modo local para la selección. Hay que añadir una vista en modo servidor (patrón `views/api/` + `API_SCREENS`) |

## 4. Evidencia ejecutada (23/11/2026)

Entorno: PostgreSQL 16.2 con pgvector (embebido), Python 3.12, Node 22.

| Comprobación | Resultado |
|---|---|
| `pytest` (API completa) | 744 pasan: 710 existentes y 34 nuevos de `test_selection_decisions.py` |
| Migraciones | `downgrade base` y `upgrade head` por la propia suite; `alembic check` sin deriva; una sola cabeza (`0010`) |
| `ruff check . --select E4,E7,E9,F` | Sin errores |
| `contracts/openapi.json` y `schema.gen.ts` | Regenerados con `export_openapi.py` y `pnpm gen:api` |
| `tsc --noEmit` y `pnpm test` (Vitest) | Sin errores; 67 pruebas pasan |

No ejecutado: `pnpm build`, E2E, `gitleaks` ni el job `compose` de CI (no hay Docker en este entorno).

## 5. Puntos de coordinación al integrar

- **Migración `0010`:** si otro PR añade también una `0010`, hay que renumerar este fichero y su `revision` al hacer el rebase. `alembic heads` debe mostrar una sola cabeza.
- **Ficheros compartidos:** `api/app/main.py` y `api/app/models.py` reciben una línea de importación cada uno, y `api/app/seed.py` un nombre más en `reset`. Los conflictos, si los hay, son de resolución trivial.
- **Cliente generado:** si otro PR cambia `contracts/openapi.json`, regenerar `schema.gen.ts` con `pnpm gen:api` tras el rebase; el CI lo comprueba.
- **Diagrama ER y diccionario de datos:** la tabla `selection_decision` es nueva. Los tests de deriva existentes (`test_data_dictionary_drift`) no la cubren y siguen pasando; conviene añadirla al diagrama de admisiones cuando se integre.
