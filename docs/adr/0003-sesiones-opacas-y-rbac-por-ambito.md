# ADR-0003 · Sesiones con token opaco y autorización por rol + ámbito

**Estado:** aceptada (F1) · **Fecha:** 2026-11-08

**Decisión.** Login con cuentas sintéticas; el servidor emite un token aleatorio y guarda solo su SHA-256 con caducidad y revocación por sesión. Contraseñas con `hashlib.scrypt`. Cada endpoint comprueba `permiso + ámbito` (global, programa, convocatoria, cohorte) a partir de `role_assignment`.

**Motivo.** Revocación inmediata y sin dependencias extra (frente a JWT); permisos acumulables y limitados por convocatoria/cohorte, como exige el TO-BE.

**Consecuencias.** Una consulta por petición para resolver la sesión (aceptable). OAuth/SSO queda fuera del alcance del proyecto.
