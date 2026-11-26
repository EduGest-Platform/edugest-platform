# KAN-278 — Eventos

## Objetivo
Añadir una tarjeta Eventos a EduGest para descubrir próximos eventos académicos.

## Alcance propuesto
- Tarjeta y navegación coherentes con el dashboard existente.
- Listado cronológico, detalle, fecha, hora y zona horaria.
- Estados de carga, vacío y error; accesibilidad y diseño responsive.
- Autorización en servidor por rol y ámbito; no exponer datos de otras cohortes.
- Evaluar creación y edición por personal autorizado con auditoría.
- Integraciones de calendario, Zoom y correo como fases posteriores, sin dependencia de PR no fusionados.

## Criterios de aceptación
- Navegación funcional y permisos positivos/negativos.
- Datos sintéticos, pruebas unitarias y E2E; CI verde.
- Validar ubicación, roles y alcance con PO antes de Ready.

Estado: listado y navegación implementados con datos locales sintéticos. La autorización del servidor y la fuente API siguen pendientes. Pruebas unitarias de navegación y filtros añadidas; pendiente validar el nuevo CI.
