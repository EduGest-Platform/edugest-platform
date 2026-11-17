# KAN-107 · Anexo 6 — Acceso dinámico por rol, categoría y convocatoria / Dynamic scoped field access

**Estado:** diseño V2 sujeto a validación PO y revisión técnica de Anas/backend. **No implementado**. Este documento **NO autoriza nuevas migraciones, endpoints, cambios de permisos o despliegues**. La implementación debe planificarse con la historia KAN-42 y la cadena Alembic compartida.

> **EN:** Role-based, call-scoped access already exists in FastAPI. Fine-grained field-group grants do not. The design below permits authorised administrators to grant or revoke temporary access to protected groups during an active call, without changing form versions or historical application data. All sensitive access requires both an existing base permission and an explicit, active per-call grant; self-grants are forbidden.

## 1. Qué pregunta resuelve

**Sí:** durante una convocatoria pueden cambiar las personas que trabajan en captación, selección o revisión, y se debe poder **otorgar/revocar accesos** por necesidad funcional. **No:** ese cambio no permite modificar indiscriminadamente el formulario, sus respuestas, las reglas de admisión ni el fundamento jurídico del tratamiento.

Hay tres conceptos independientes:

- **Identidad/rol/ámbito:** quién es el usuario y qué puede hacer en el programa o convocatoria. `RoleAssignment` y `Principal.can()` ya existen en `api/app/core/authz.py`; no existe en `dev` un flujo administrativo completo de alta/revocación desde la UI.
- **Grupo de datos protegido:** qué **tipo** de información puede consultar, además de su permiso base (`G3` origen/género; `G6` situación de vulnerabilidad). No existe todavía control granular ni concesión persistida en `dev`.
- **Versión de formulario:** qué campos/opciones se mostraron en una inscripción. No cambia al modificar permisos, y sus respuestas históricas no se vuelven a escribir.

## 2. Política de acceso propuesta (deny by default)

| Grupo de datos | Ejemplos | Personal con acceso operativo base en su ámbito | ¿Requiere concesión extra de grupo? | Dónde se puede ver |
|---|---|---|---|---|
| `G1/G2` | Identidad, correo, teléfono, año de nacimiento | Captación y selección según tareas; administración con necesidad acreditada | No, pero con RBAC y ámbito | Pantallas de contacto y detalle autorizadas; nunca público |
| `G4/G5/G7` | Residencia, experiencia, procedencia del contacto | Captación/selección si necesario | No, pero ámbito + finalidad | Detalle y solo campos mínimos en listado |
| `G3` | País de nacimiento, nacionalidad, género | Solo personas con permiso base de expediente | **SÍ: autorización G3 vigente y por `call_id`** | Únicamente detalle autorizado; no listados, exportaciones genéricas o logs |
| `G6` | Situación personal, incluida discapacidad | Solo personas con permiso base de expediente | **SÍ: autorización G6 vigente y por `call_id`** | Únicamente detalle autorizado; proteger el campo completo si contiene respuestas especiales |
| `G8/G9` | Acuse de información, referencia de auditoría | Personal autorizado según acción; auditoría solo `audit.read` | Según acción | No publicar datos de auditoría ni notas CRM |

**Regla de lectura G3/G6:**

```text
permitir_lectura(usuario, candidatura, grupo) SI Y SOLO SI
  sesion_vigente
  AND usuario_tiene_permiso('applications.read', scope_de_la_candidatura)
  AND existe_concesion_activa(usuario.id, candidatura.call_id, grupo, 'read')
  AND concesion.no_expirada AND concesion.no_revocada
  AND finalidad_aprobada_para_esa_convocatoria
```

Ningún permiso `admin:*` puede **sustituir** por sí solo la comprobación explícita del grupo protegido. El administrador que **gestiona** las concesiones no recibe por ello acceso de **lectura**. Las decisiones de quién puede aprobarlas en la Fundación deben registrarse; en la demo se usan únicamente sujetos ficticios.

**No reutilizar** un permiso de la convocatoria A para la B. Los permisos de `program` existentes siguen controlando el expediente base; las concesiones sensibles se concretan siempre en `call_id`.

## 3. ¿Quién puede cambiar permisos mientras está abierta la convocatoria?

1. **Solicitante interno autorizado**: pide dar acceso G3 o G6 a un integrante para una finalidad concreta, por un período y una convocatoria determinada.
2. **Responsable funcional/Data Owner designado**: valida necesidad y atribución, con evidencia de aprobación; no equivale al DPO. La identidad y competencias reales de este cargo quedan pendientes de definir con la Fundación.
3. **Administrador autorizado (`data_access.manage`)**: ejecuta la concesión o revocación; no puede aprobar ni concederse a sí mismo un acceso sensible. Para la demo puede simularse el flujo con dos usuarios sintéticos.
4. **FastAPI**: valida rol, ámbito, aprobación y límites, guarda la concesión y la auditoría; la revocación y la expiración surten efecto desde **la siguiente petición**, sin depender de un botón oculto en React ni de un logout.
5. **Revisión periódica**: el acceso caduca como máximo en la fecha definida por la aprobación. Para gestiones posteriores al cierre de la convocatoria se requiere motivo y vigencia explícitos, no un acceso perpetuo por inercia.

No se permite asignar `data_access.manage` desde la propia interfaz sin un proceso de administración de roles autorizados, ni permitir que un gestor conceda permisos a su propio `user_id`.

## 4. Modelo de datos conceptual, no SQL ni migración

**Propuesta para evaluar con la persona responsable de backend y KAN-42:** almacenar las concesiones temporales en un objeto o entidad `FieldAccessGrant` **solo cuando se apruebe su implementación**. No crear tablas ni Alembic desde KAN-107.

| Atributo lógico | Propósito |
|---|---|
| `subject_user_id` | Persona del equipo a la que se concede el permiso |
| `call_id` | Convocatoria exacta a la que se limita |
| `field_group` | `G3` o `G6` (lista cerrada) |
| `action` | `read` (MVP); nada de editar o exportar sensibles por defecto |
| `purpose_code` | Motivo registrado (catálogo, no texto libre que contenga PII) |
| `approved_by_user_id` | Aprobador funcional válido, distinto del beneficiario |
| `granted_by_user_id` | Administrador ejecutor, distinto del beneficiario |
| `valid_from`, `expires_at` | Ventana temporal obligatoria |
| `revoked_at`, `revoked_by_user_id` | Revocación manual y su autor |
| `created_at` | Trazabilidad |

**Control transaccional:** garantizar que la concesión y su evento de auditoría se confirmen juntos; denegar sobre errores, expiración, rol revocado o grupo desconocido. Auditar también la lectura de G3/G6, registrando `actor_user_id`, `call_id`, `application_id`, `field_group`, acción y resultado **sin valores de los campos**. Esos identificadores pueden seguir siendo datos personales seudonimizados: aplicar retención de auditoría.

**No crear un tipo de rol nuevo** para cada grupo. Preferir permisos operativos específicos y concesiones por grupo, manteniendo `RoleAssignment` para el ámbito general. El modelo final se decidirá tras revisar schema, requisitos de servicio y capacidad temporal.

## 5. Contratos conceptuales (no rutas aprobadas)

- **Gestión de concesiones:** endpoints administrativos **a definir** con `data_access.manage`, comprobación de aprobador, no auto-concesión, razón y expiración. No implementar CRUD genérico de permisos ni usar `PATCH` de roles sin validación.
- **Lectura de expediente:** `GET /api/v1/applications/{id}` devuelve campos generales según rol/ámbito y **omite** completamente G3/G6 sin concesión válida. Considerar `403` si se solicita un recurso exclusivamente protegido. No enviar valores con `null` si la UI puede interpretarlos como ausentes o no respondidos; señalar autorización mediante un indicador seguro sin revelar datos.
- **Endpoint público del formulario:** solo contiene campos visibles y validaciones públicas; jamás la matriz de permisos, cuotas internas ni otros criterios no aprobados.
- **Frontend:** apartado «Accesos de convocatoria» para personal autorizado (fase de implementación); debe mostrar quién tiene acceso G3/G6, cuándo caduca y permitir solicitar revocación, con explicación de que la aprobación tiene autoridad limitada.
- **Candidatura/versión:** `form_version_id` y respuestas históricas no se modifican al conceder o retirar permisos.

## 6. Ejemplo sintético (dos convocatorias)

- Un miembro de `seleccion` tiene `applications.read` para **CONV-IA-A**. Sin G6 ve datos de contacto y estado, pero no situación personal.
- El administrador autorizado tramita una concesión **G6/CONV-IA-A**, aprobada por la función competente y válida tres días. A partir de entonces el integrante ve esa sección solo en expedientes de CONV-IA-A.
- En **CONV-DATA-B**, aunque tenga otra asignación general, **no ve G6** sin concesión separada.
- Si la revocan antes de los tres días, el siguiente GET deja de devolver G6. Los datos de la candidatura y el formulario permanecen intactos.
- Una persona `docente`, `coder` o `coordinacion` sin el permiso base de expediente no puede conseguir lectura con solo una concesión G6.

## 7. Pruebas negativas y evidencias necesarias

- Concesión válida, expiración, revocación inmediata, diferente `call_id` y rol base revocado.
- Intento de auto-concederse acceso; intentos por operador sin `data_access.manage`; aprobación inválida.
- Lectura sin G3/G6 no revela ni un valor en API, lista, notas, logs, auditoría, exportaciones o errores.
- El administrador gestiona sin acceder automáticamente al dato; personal con acceso operativo puede consultar sin modificar privilegios.
- Misma candidatura, versión y respuestas antes/después de otorgar/revocar.
- Comprobar que `current_situation` se protege como un solo grupo de sensibilidad máxima si incluye `disability`.
- Pruebas con PostgreSQL sintético, contrato OpenAPI/TS sincronizados, CI y revisión por otra persona. **Todas estas pruebas están pendientes; ninguna es PASS.**

## 8. Alcance y migraciones

**KAN-107:** solo propuesta y documentación (este anexo).

**KAN-42:** implementación y pruebas del formulario y de los controles mínimos necesarios para que no se expongan G3/G6; el equipo podrá separar la gestión administrativa avanzada en una iteración distinta, siempre que no presente la funcionalidad dinámica como disponible. No incluir datos sensibles en una demo de servidor donde falten los controles.

**Alembic:** ninguna revisión nueva en esta entrega; coordinación de backend con la cadena única y el HEAD real, según el [Entregable 4](kan-107-4-plan-implementacion.md). No reservar IDs ni crear HEADs paralelos.

**EN acceptance summary:** Access grant/revoke must be authorised, scoped to one call, time-bounded, effective on the next API request, audited without field values, non-self-service and independent from form version. This is a **planned implementation** only; the project must not claim it works until tested.

## English edition (equivalent sections, KAN-107 V2)

**Status.** Proposed design, **not implemented**; it authorises no migrations, endpoints, permission changes or deployments. Implementation belongs to KAN-42 and the shared Alembic chain.

**§1 Question solved.** Staff working on intake, selection or review can change during a call, so access must be grantable and revocable by functional need. That does not allow arbitrary changes to the form, answers, admission rules or lawful basis.

**§2 Policy (deny by default).** G1/G2 identity and age, G4/G5/G7 residence, experience and channel: base role and scope. G3 (origin, gender) and G6 (personal situation, incl. disability): `applications.read` is necessary but insufficient; an explicit, active grant for that `call_id` is also required. G8/G9 follow the action; audit needs `audit.read`. Read rule: valid session AND `applications.read` in scope AND active, non-expired, non-revoked grant for that call and group AND approved purpose.

**§3 Who can change permissions during a call.** (1) Authorised internal requester asks; (2) the **responsible functional owner / Data Owner approves** (not the DPO; identity pending with the Foundation); (3) the **authorised administrator (`data_access.manage`) executes** the grant or revocation and cannot approve or self-grant; (4) FastAPI enforces role, scope, approval and limits from the next request; (5) grants expire and are reviewed.

**§4–§6.** Conceptual `FieldAccessGrant` (no tables or Alembic from KAN-107), conceptual contracts (not approved routes), synthetic two-call example.

**§7 Negative tests (all pending, none PASS).** Valid grant, expiry, immediate revocation, different `call_id`, revoked base role, self-grant, operator without `data_access.manage`, no leakage via API/list/notes/logs/exports/errors, unchanged form version and answers, `current_situation` protected as a single group when it includes `disability`.

**§8 Scope.** KAN-107 = proposal and documentation; KAN-42 = implementation and tests; Alembic = no new revision here.
