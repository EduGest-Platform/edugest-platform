# 03 · Reparto, pruebas, riesgos y revisión crítica

## Cinco frentes (sin asignación nominal)

| Frente | Responsabilidad | Parte de | Primer entregable |
|---|---|---|---|
| **A** Plataforma | API base, migraciones, sesiones, RBAC, auditoría, contratos, CI, compose, despliegue | F1 (hecho) | Validar compose y CI reales; despliegue de prueba |
| **B** Admisión / CRM | Requisitos por convocatoria, revisión humana, puntuación versionada, decisión conjunta, cupos/reserva, matrícula, tareas del 70 % | `views/api/ApiAdmissions.tsx`, `modules/admissions` | US-02/US-03 y puerta del 18/11 |
| **C** Académico | Persistir competencias, rúbricas, evaluaciones, asistencia y calendario; vistas docente/coder | `actions.ts`, `analytics.ts`, vistas académicas | `GET /cohorts/{id}/competencies` + evaluación persistida |
| **D** RAG / feedback | Corpus autorizado, chunking, pgvector, `/assistant/ask` con citas y abstención, banco de pruebas, borrador de feedback | `views/Assistant.tsx`, `documentos` | Banco de 20–30 preguntas antes de la UI |
| **E** ML / evaluación | Dataset sintético, baseline, model card, matriz ética, informe del 70 %, pruebas negativas transversales | `applyAbsenceRule`, `audit_event` | Generador sintético reproducible |

Reglas: un responsable y una persona revisora por historia; PR pequeñas; cambios de API, permisos o IA con revisión cruzada; máximo dos hitos críticos en integración simultánea.

## Puertas de calidad y criterios de aceptación

| Puerta | Criterio verificable |
|---|---|
| **12/11 · F1** | (1) web arranca igual sin API, 16 Vitest + build; (2) `alembic upgrade/downgrade/check` en PostgreSQL vacío; (3) inscripción crea `Person`+`Application`, duplicado → 409, otra convocatoria reutiliza `Person`; (4) 401 sin sesión, 403 fuera de ámbito (captación cruzada, docente, persona); (5) cada escritura y lectura de expediente audita; (6) contrato exportado y cliente TS compila; (7) dos navegadores ven la misma candidatura. **Estado: cumplido en sandbox** (ver incremento F1); compose y CI pendientes de ejecución real. |
| **18/11 · F2** | Aspirante → requisitos → puntuación humana (rúbrica versionada) → decisión conjunta → admitida/reserva/no admitida → `Enrollment` de la misma `Person`; ≥3 excepciones (incompleta, retirada, reserva) sin decisión automática. |
| **23/11 · F3** | Un coder sintético recibe evaluación persistida con versión de rúbrica; docente de otra cohorte recibe 403. |
| **25/11 · F4** | RAG responde con cita o se abstiene; no recupera documentos de otra cohorte; alerta de riesgo explicada y revisada; feedback borrador publicado solo tras revisión. |
| **30/11 · RC** | E2E completo con Playwright, permisos por rol en todos los endpoints, informe del 70 % con ≥100 casos, model card, matriz ética, manuales. |
| **04/12** | Demo estable, respaldo local, evidencias y defensa ensayada. |

Pirámide: Vitest (dominio web) · pytest sobre PostgreSQL (API, RBAC, migraciones, concurrencia) · E2E (`e2e/`) · evaluaciones offline (RAG, ML, 70 %) en `evals/`.

## Riesgos y simplificaciones

| Riesgo | Sev. | Mitigación |
|---|---|---|
| La preview de Make no alcanza un backend | Alta | Modo local por defecto en Make; modo servidor en local/despliegue propio (ADR-0004) |
| compose/CI no verificables en el sandbox | Media | Validarlos el 10–12/11; pytest ya corre en PostgreSQL real |
| Divergencia de modelo entre frentes | Crítica | Contrato generado + prueba de deriva; cambios de API revisados por A |
| Enumeración de correos (409 en inscripción) | Media | Aceptado para la demo (UX); en producción: respuesta genérica + aviso por correo |
| 70 % inflado | Alta | Solo tareas elegibles de preselección, frecuencias explícitas, aprobación de Melissa |
| RAG con fugas o alucinaciones | Alta | Filtro de ámbito antes de recuperar, abstención, métricas publicadas |
| Ejecución de código no confiable | Alta | No se ejecuta: tests precomputados y etiquetados |
| Bundle > 500 kB | Baja | División por rutas (`React.lazy`) en F5 |

Simplificaciones recomendadas: autenticación demo sin OAuth ni recuperación de contraseña; LLM opcional tras interfaz con base extractiva reproducible; correo como cola registrada sin envío; GitHub como enlaces de portfolio; HubSpot solo por CSV si se acuerda.

## Revisión crítica

- **Product Owner.** El valor del 18/11 es el recorrido aspirante → coder; F1 resuelve identidad única y CRM mínimo, no la decisión. No ampliar vistas académicas hasta conectar la admisión. POR VALIDAR: definición del 70 % (A8) y quién firma la decisión conjunta.
- **Arquitectura.** Se desvía de v1.2 en dos puntos: la web permanece en la raíz (Make) y `Call` es entidad de primer nivel (ámbito de preselección). El conmutador local/API introduce dos fuentes durante la transición: cada vista debe migrarse completa, nunca mezclar datos de ambas.
- **Seguridad.** RBAC y auditoría ya están en servidor. Pendiente: limitación de intentos de login, cabeceras de seguridad y HTTPS en despliegue, rotación de la contraseña demo, retención de sesiones. El modo local sigue siendo inseguro por diseño y no debe desplegarse como producto.
- **Ingeniería de IA.** Nada de F1 es IA. Retirar etiquetas «IA» de contenido semilla en F4; el modelo de riesgo con etiquetas sintéticas solo demuestra el pipeline; el RAG necesita banco de pruebas antes de interfaz.
- **QA.** F1 versiona por primera vez las pruebas de navegador. Siguen faltando: E2E en CI (requiere servicios), pruebas de accesibilidad automáticas y Playwright.
