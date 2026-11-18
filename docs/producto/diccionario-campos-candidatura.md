# Diccionario de campos de candidatura / Application field dictionary

**Jira:** KAN-92 (inventario y fuentes) · KAN-93 (formulario real, alcance y obligatorios) · Historia KAN-43 (PF2-WEB-05)
**Autor:** Anas · **Revisión:** Elizabeth (PO) · **Estado:** borrador revisado tras la revisión del 18/11/2026

> **Importante: esto es una foto de formularios concretos, no "el formulario de Somos F5".** Cada formación tiene su propio formulario y las opciones cambian entre convocatorias. Cada tabla dice de qué formulario sale, con su URL y su fecha.
>
> **EN summary:** Snapshot of specific Somos F5 application forms (each training has its own form, and options change between calls), compared with what EduGest collects today, with a proposed scope per field. Form A was captured from the live page; Form B is described by the team and still needs verification. Scope is a proposal: the PO decides. EduGest only uses synthetic data.

## 1. Fuentes

| Fuente | Qué aporta | Fecha |
|---|---|---|
| **Formulario A** (en vivo): `https://landings.somosf5.org/proyecto-ai4inclusion-bootcamp` · formulario HubSpot, portal `143924699`, ID `4ed218bc-9bde-4fe0-8dba-855fd733ef27` | Tabla de la sección 3 (campos, tipos, obligatorios y textos exactos de las opciones) | Capturado el 17/11/2026, solo lectura, sin enviar nada. El 18/11/2026 la página ya dice "Las inscripciones están cerradas" y el formulario no aparece: no se puede volver a comprobar |
| **Formulario B** (descrito por el equipo) | Tabla de la sección 4 | Descrito en la revisión del 18/11/2026. **URL pendiente; no verificado en vivo** |
| Correo de Melissa "Aclaraciones AS IS" ([Drive](https://drive.google.com/file/d/1NEjbsqzwke5JGAhySVmFzadMq-KXrGUx/view)) | Confirma que el formulario de la landing es la primera etapa de inscripción | 06/11/2026 |
| AS-IS preselección v1.0 ([Drive](https://drive.google.com/file/d/1JoY3DKfuNPJf4-JC7eJugVejIusrET5K/view)) | Las respuestas acaban en Google Sheets / HubSpot y se revisan caso a caso, sin exclusión automática | 08/11/2026 |
| `contracts/openapi.json` → `ApplicationCreate` | Lo que nuestra API acepta hoy | rama `dev`, 17/11/2026 |

## 2. Cómo era el Formulario A

- Formulario **HubSpot** incrustado en la landing (`forms-eu1.hsforms.com`), con reCAPTCHA invisible.
- **Una sola etapa** (una página), sin pasos.
- Aviso visible: *esta edición está abierta a personas que residen en la provincia de Madrid*.
- Botón de envío: **Enviar**.

## 3. Campos del Formulario A (capturado el 17/11/2026)

Leyenda de alcance (propuesta): **MVP** = lo construimos ahora · **PO** = decide Elizabeth antes de construir · **Fuera** = no entra en la demo.

| # | Campo visible (texto real) | Tipo | ¿Obligatorio? | Opciones | ¿Lo tenemos hoy en EduGest? | Alcance propuesto | Nota |
|---|---|---|---|---|---|---|---|
| 1 | Nombre | Texto | Sí | — | Sí, como `nombre` (nombre completo) | MVP | Separar en nombre y apellidos |
| 2 | Apellidos | Texto | Sí | — | No (va dentro de `nombre`) | MVP | |
| 3 | Correo | Email | Sí | — | Sí, `email` | MVP | En la demo, solo dominios reservados (`@example.test`) |
| 4 | Número de teléfono | Teléfono con prefijo de país | Sí | Selector de país | No | MVP | Para recordatorios y llamadas de captación (AS-IS). Solo números ficticios |
| 5 | Año de nacimiento | Desplegable con búsqueda | Sí | Lista de años | No | MVP | Solo el año, no la fecha completa (minimización) |
| 6 | ¿En qué país naciste? | Desplegable con búsqueda | Sí | Lista de países | No | PO | Dato con riesgo de discriminación. ¿Lo pide la entidad financiadora? |
| 7 | Nacionalidad | Desplegable con búsqueda | Sí | Lista de países | No | PO | Dato con riesgo de discriminación. Mismo caso que el 6 |
| 8 | ¿Con qué género te identificas? | Desplegable con búsqueda | Sí | No capturadas en el Formulario A (lista desplegable; el formulario ya está cerrado). Ver el Formulario B | No | PO | Si se mantiene: con "Prefiero no identificarme", y solo para estadísticas agregadas de sesgo (Matriz de Evaluación Ética) |
| 9 | ¿En qué provincia de España o distrito de Portugal resides? | Desplegable con búsqueda (un solo campo) | Sí | Provincias y distritos | No | MVP | Requisito de residencia. Se revisa, nunca excluye solo |
| 10 | Detalla brevemente tu experiencia previa o conocimientos en programación | Texto largo | Sí | — | Parcial: tenemos `motivacion`, que es otra pregunta | MVP | Campo propio |
| 11 | ¿En qué situación te encuentras actualmente? Marca todas las casillas correspondientes | Casillas (varias) | Sí | Cabeza de familia monoparental · Desempleada/o (inferior a 3 meses) · Desempleada/o de larga duración · Discapacidad · En riesgo de exclusión social · Inmigrante · Joven sin titulación y sin empleo · Mujer en situación de vulnerabilidad · No me identifico con ninguna de las opciones anteriores · Refugiada/o · Joven de menos de 30 años · Persona con acceso limitado a recursos, servicios o oportunidades vitales | No | MVP (con cuidado) | Incluye datos de categoría especial (discapacidad). Revisión humana, nunca exclusión automática. Las opciones cambian entre formularios (ver B) |
| 12 | ¿Cómo nos has conocido? | Casillas (varias) | Sí | Amig@s o conocid@s · Entidad, fundación o programa social · Redes sociales (Instagram, LinkedIn, YouTube, TikTok) · Fundación Tomillo · Fundación Federico Ozanam · Stellantis · Otros | No | MVP | Métricas de captación por canal. Las opciones cambian entre formularios (ver B) |
| 13 | Acepto recibir otras comunicaciones de Somos F5. | Casilla | No | — | No | Fuera | La demo no envía comunicaciones reales |
| 14 | Acepto que Somos F5 almacene y trate mis datos personales. | Casilla | Sí | — | **No** | MVP | `acepta_datos_sinteticos` es un aviso de demo, no un consentimiento de tratamiento de datos. Hace falta un consentimiento propio |

## 4. Diferencias del Formulario B (descrito por el equipo, sin verificar)

Solo se listan los campos que cambian respecto al Formulario A. **Pendiente:** URL y fecha del Formulario B para poder comprobarlo.

| Campo | Formulario B (según el equipo) | Alcance propuesto | Nota |
|---|---|---|---|
| Género (#8) | Desplegable obligatorio: Mujer · Hombre · Otro (con un texto entre paréntesis, por confirmar) · No binario · Prefiero no identificarme | PO | |
| Residencia (#9) | Dos campos: **Municipio** (texto libre) y **Comunidad autónoma** (desplegable). Sin opción de distrito de Portugal (por confirmar) | MVP | |
| Experiencia en programación (#10) | No aparece en la versión descrita (por confirmar) | — | |
| Situación actual (#11) | 8 opciones: Migrante o refugiada · Familia monoparental · Víctima de violencia de género y/o trata · En situación de desempleo · Mujer con discapacidad · Acceso limitado a recursos, servicios y oportunidades esenciales · Afronto otros desafíos sociales · No me encuentro en ninguna de las situaciones anteriores | MVP (con cuidado) | Sin "Joven de menos de 30 años". Incluye categorías especiales (salud, violencia de género) |
| Cómo nos has conocido (#12) | Obligatorio. Añade Factoría F5, Peñascal, SSCUB y Arrabal EAID; no aparece Stellantis | MVP | |
| **Certificado de discapacidad** (nuevo) | Una sola respuesta: certificado ≥33 % · certificado <33 % · certificado de incapacidad · discapacidad/incapacidad en trámite. ¿Obligatorio? Por confirmar | PO | **Dato de salud: categoría especial (RGPD art. 9)** |
| **Entidad que te deriva** (nuevo) | Texto libre obligatorio con el nombre de la entidad social | MVP | |

## 5. Campos que tenemos en EduGest y los formularios no

| Campo EduGest | Motivo para mantenerlo |
|---|---|
| Convocatoria (`call_id`) | Una persona puede aplicar a varias convocatorias con un único expediente |
| Disponibilidad (Mañana / Tarde / Flexible) | Útil para organizar jornadas |

## 6. Observaciones de accesibilidad del Formulario A

Para no repetirlas en el nuestro:
- Los desplegables con búsqueda añaden campos "Buscar" sin etiqueta propia; un lector de pantalla los lee como "Buscar" sin contexto.
- En los grupos de casillas, cada casilla aparece marcada como obligatoria, cuando la regla real es "marca al menos una".
- Los obligatorios se indican solo con `*`, sin texto que lo explique.

## 7. Qué falta decidir

- **Respondido por el equipo (18/11/2026):** país de nacimiento/nacionalidad/género, disponibilidad y separar nombre/apellidos. Falta copiar aquí la respuesta concreta de cada una cuando la PO la confirme por escrito.
- **Abierto:** como cada formación tiene su formulario, ¿EduGest necesita un formulario configurable por convocatoria (KAN-42) con un conjunto mínimo común de campos? Proponemos que la PO fije ese conjunto mínimo.
- **Abierto:** URL del Formulario B y confirmación de los puntos marcados "por confirmar".

## 8. Siguiente paso

Cuando la PO cierre el alcance: Elizabeth actualiza `ApplicationCreate` en la API y el contrato (KAN-107); Anas adapta el formulario (KAN-42 / KAN-125) con `pnpm gen:api`.
