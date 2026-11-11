# ADR-0004 · Conmutador de fuente de datos local / API

**Estado:** aceptada (F1) · **Fecha:** 2026-11-08

**Decisión.** `VITE_GISTAR_API_URL` activa el modo servidor. Sin ella la web es idéntica al prototipo (localStorage). En modo servidor, las vistas migradas (`API_VIEWS`) usan la API y el resto muestran un aviso de datos locales. La sesión se guarda en `sessionStorage` (una por pestaña).

**Motivo.** La preview de Make no puede alcanzar un backend; el equipo necesita migrar vista a vista sin romper la demo.

**Consecuencias.** Durante la transición conviven dos fuentes: cada vista se migra completa y se retira su ruta local cuando todas estén conectadas (F5). Nunca se mezclan datos de ambas en una misma vista.
