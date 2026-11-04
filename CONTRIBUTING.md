# Guía de contribución — EduGest

## Flujo de trabajo

- `main`: versión estable; no se trabaja directamente.
- `dev`: rama de integración; no se trabaja directamente.
- `feature/<issue>-<descripcion>`: rama para cada tarea.
- `fix/<issue>-<descripcion>`: rama para correcciones.

## Antes de empezar

1. Comprueba que tienes asignada una Issue.
2. Actualiza `dev`:
   ```bash
   git checkout dev
   git pull origin dev
   ```
3. Crea una rama de trabajo:
   ```bash
   git checkout -b feature/12-descripcion
   ```

## Commits

Usa mensajes claros, por ejemplo:

- `feat: add student registration`
- `fix: validate enrollment data`
- `docs: update project setup`
- `test: add enrollment tests`
- `chore: configure repository`

## Pull Requests

- Todo PR de funcionalidad debe dirigirse a `dev`.
- Relaciona la PR con su Issue usando `Closes #12`.
- Explica qué cambia, cómo probarlo y cualquier limitación.
- Solicita revisión a una persona distinta de quien creó el PR.
- Resuelve las conversaciones y aplica los cambios solicitados.
- No integres cambios sin la aprobación requerida por GitHub.

La promoción de `dev` a `main` se realizará mediante un PR de versión estable, coordinado por la persona responsable del repositorio.

## Calidad

- No incluyas contraseñas, tokens, claves API ni datos personales reales.
- Mantén los cambios acotados a la Issue.
- Añade o actualiza pruebas cuando corresponda.
- Documenta las decisiones técnicas en `docs/`.
