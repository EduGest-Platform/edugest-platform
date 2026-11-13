# ADR-0002 · FastAPI como monolito modular sobre PostgreSQL

**Estado:** aceptada (F1) · **Fecha:** 2026-11-08

**Decisión.** Un único servicio FastAPI con un `APIRouter` por dominio, SQLAlchemy 2, migraciones Alembic revisadas a mano y PostgreSQL 16 (pgvector disponible para F4). Las pruebas se ejecutan contra PostgreSQL, no SQLite.

**Motivo.** Cinco personas y cuatro semanas: un monolito con fronteras de módulo evita la coordinación de microservicios y mantiene un único expediente. pgvector evita un servicio vectorial adicional.

**Consecuencias.** Triggers y restricciones de PostgreSQL forman parte del diseño (p. ej. auditoría de solo inserción). Desarrollo local requiere PostgreSQL (compose o instalación).
