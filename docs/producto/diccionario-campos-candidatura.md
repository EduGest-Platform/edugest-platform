# Diccionario de campos de candidatura / Application field dictionary

**Jira:** KAN-92 (inventario y fuentes) · KAN-93 (formulario real, alcance y obligatorios) · Historia KAN-43 (PF2-WEB-05)
**Autor:** Anas · **Revisión:** Elizabeth (PO) · **Estado:** borrador para revisar · **Fecha de captura:** 17/11/2026

> **EN summary:** This is the list of fields in the real Somos F5 application form (HubSpot), captured on 17/11/2026, compared with what EduGest collects today, with a proposed scope for each field. Scope is a proposal: the PO decides. Our platform only uses synthetic data.

## 1. Fuentes

| Fuente | Qué aporta | Fecha |
|---|---|---|
| Formulario real: `https://landings.somosf5.org/proyecto-ai4inclusion-bootcamp` (parte inferior de la página) | Los campos, tipos y obligatorios de este documento | Consultado el 17/11/2026 (solo lectura, no se envió nada) |
| Correo de Melissa "Aclaraciones AS IS" (Drive) | Confirma que este formulario es la primera etapa de inscripción | 06/11/2026 |
| AS-IS preselección v1.0 (Drive) | Las respuestas acaban en Google Sheets / HubSpot y se revisan caso a caso, sin exclusión automática | 08/11/2026 |
| `contracts/openapi.json` → `ApplicationCreate` | Lo que nuestra API acepta hoy | rama `dev`, 17/11/2026 |

## 2. Cómo es el formulario real

- Es un formulario **HubSpot** incrustado en la landing (`forms-eu1.hsforms.com`), con reCAPTCHA invisible.
- Tiene **una sola etapa** (una página). No hay pasos ni formulario por fases.
- Aviso visible: *esta edición está abierta a personas que residen en la provincia de Madrid*.
- Texto de confianza: el bootcamp se dirige a personas con barreras para acceder a un empleo de calidad; las respuestas se tratan de forma confidencial.
- Botón de envío: **Enviar**.

## 3. Campos

Leyenda de alcance (propuesta): **MVP** = lo construimos ahora · **PO** = decide Elizabeth antes de construir · **Fuera** = no entra en la demo.

| # | Campo visible (texto real) | Tipo | ¿Obligatorio en el real? | Opciones | ¿Lo tenemos hoy en EduGest? | Alcance propuesto | Nota |
|---|---|---|---|---|---|---|---|
| 1 | Nombre | Texto | Sí | — | Sí, como `nombre` (nombre completo) | MVP | Separar en nombre y apellidos |
| 2 | Apellidos | Texto | Sí | — | No (va dentro de `nombre`) | MVP | |
| 3 | Correo | Email | Sí | — | Sí, `email` | MVP | En la demo, solo dominios reservados (`@example.test`) |
| 4 | Número de teléfono | Teléfono con prefijo de país | Sí | Selector de país | No | MVP | Necesario para recordatorios y llamadas de captación (AS-IS). Solo números ficticios |
| 5 | Año de nacimiento | Desplegable con búsqueda | Sí | Lista de años | No | MVP | Solo el año, no la fecha completa (minimización). Sirve para el criterio "joven de menos de 30 años" |
| 6 | ¿En qué país naciste? | Desplegable con búsqueda | Sí | Lista de países | No | PO | Dato sensible. ¿Lo pide la entidad financiadora? |
| 7 | Nacionalidad | Desplegable con búsqueda | Sí | Lista de países | No | PO | Dato sensible. Mismo caso que el 6 |
| 8 | ¿Con qué género te identificas? | Desplegable con búsqueda | Sí | No capturadas (lista desplegable) | No | PO | Si se mantiene: opcional, con "Prefiero no decirlo", y solo para estadísticas agregadas de sesgo (Matriz de Evaluación Ética) |
| 9 | ¿En qué provincia de España o distrito de Portugal resides? | Desplegable con búsqueda | Sí | Provincias y distritos | No | MVP | Requisito de residencia (esta edición: Madrid). Se revisa, nunca excluye solo |
| 10 | Detalla brevemente tu experiencia previa o conocimientos en programación | Texto largo | Sí | — | Parcial: tenemos `motivacion` | MVP | Añadirlo como campo propio; la motivación es otra pregunta |
| 11 | ¿En qué situación te encuentras actualmente? Marca todas las casillas correspondientes | Casillas (varias) | Sí | Cabeza de familia monoparental · Desempleada/o (inferior a 3 meses) · Desempleada/o de larga duración · Discapacidad · En riesgo de exclusión social · Inmigrante · Joven sin titulación y sin empleo · Mujer en situación de vulnerabilidad · No me identifico con ninguna de las opciones anteriores · Refugiada/o · Joven de menos de 30 años · Persona con acceso limitado a recursos, servicios o oportunidades vitales | No | MVP (con cuidado) | Datos de categoría especial (discapacidad, situación social). Criterios según financiador; revisión humana, nunca exclusión automática |
| 12 | ¿Cómo nos has conocido? | Casillas (varias) | Sí | Amig@s o conocid@s · Entidad, fundación o programa social · Redes sociales (Instagram, LinkedIn, YouTube, TikTok) · Fundación Tomillo · Fundación Federico Ozanam · Stellantis · Otros | No | MVP | Útil para métricas de captación por canal |
| 13 | Acepto recibir otras comunicaciones de Somos F5. | Casilla | No | — | No | Fuera | La demo no envía comunicaciones reales |
| 14 | Acepto que Somos F5 almacene y trate mis datos personales. | Casilla | Sí | — | Parcial: `acepta_datos_sinteticos` | MVP | Mantener nuestro aviso de datos sintéticos + texto de consentimiento claro |

**Campos que tenemos nosotros y el formulario real no:**

| Campo EduGest | Motivo para mantenerlo |
|---|---|
| Convocatoria (`call_id`) | Una persona puede aplicar a varias convocatorias con un único expediente |
| Disponibilidad (Mañana / Tarde / Flexible) | Útil para organizar jornadas; confirmar con la PO si se pregunta aquí o más tarde |

## 4. Observaciones de accesibilidad del formulario real

Para no repetirlas en el nuestro:
- Los desplegables con búsqueda añaden campos "Buscar" sin etiqueta propia; un lector de pantalla los lee como "Buscar" sin contexto.
- En los grupos de casillas, cada casilla aparece marcada como obligatoria, cuando la regla real es "marca al menos una".
- Los obligatorios se indican solo con `*`, sin texto que lo explique.

## 5. Preguntas para la PO (Elizabeth)

1. ¿País de nacimiento, nacionalidad y género son exigencia del financiador? Si no, proponemos no pedirlos (minimización de datos, RGPD).
2. ¿La lista de "situación actual" es fija o cambia según la convocatoria y el financiador? (afecta a si el formulario debe ser configurable, KAN-42)
3. ¿Disponibilidad se pregunta en la inscripción o después de la jornada informativa?
4. ¿Separamos ya `nombre` en nombre y apellidos en la API? (cambio de contrato: lo haría Elizabeth)

## 6. Siguiente paso

Cuando la PO cierre el alcance: Elizabeth actualiza `ApplicationCreate` en la API y el contrato; Anas adapta el formulario (KAN-42 / KAN-125) con `pnpm gen:api`.
