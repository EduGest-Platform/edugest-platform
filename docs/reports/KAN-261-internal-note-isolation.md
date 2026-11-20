# KAN-261 — Internal note isolation / Aislamiento de notas internas

## ES

Incremento parcial de QA sobre dev `26e5199`: cinco casos de integración de las superficies ya persistidas (nota CRM, motivos de revisión con dos versiones y motivo de decisión de preselección). No se implementa colaboración futura ni se amplían permisos; la historia AMP completa requiere aceptación de capacidad y sus dependencias.

Los tests escriben cuatro marcadores sintéticos distintos mediante API y comprueban primero que administración puede leerlos en el lugar autorizado. Así una respuesta vacía o un fixture que no se guardó no puede dar un falso positivo. La prueba de persona usa una candidatura realmente vinculada al usuario autenticado: tanto aspirante como coder ven el estado `convocada`, pero la proyección propia mantiene solo los siete campos públicos del expediente. Parámetros include/expand/fields no abren el historial interno.

Se comprueban denegaciones en ficha de personal, revisiones y versiones, decisiones, ejecuciones y auditoría. Personal de otro programa y anónimos reciben errores sin los marcadores. Los endpoints autorizados conservan sus datos: no se corrige una fuga eliminando notas de todas las respuestas. Auditoría filtrada por candidatura mantiene acciones de creación/revisión/decisión pero no copia ninguno de los textos. El logger de aplicación se comprueba en escrituras correctas, lectura, denegación y error 422 con entrada inválida.

No promete ausencia de datos sensibles en texto libre, ni anonimización global, retención, exportaciones, prompts de IA o nuevas vistas no implementadas. Protege las proyecciones/rutas concretas probadas; no certifica seguridad total. Ningún secreto ni dato real en fixtures.

## EN

Partial KAN-261 QA increment for integrated CRM notes, versioned requirement reasons and human preselection reasons. Five API/PostgreSQL cases persist distinct synthetic canaries and include positive staff reads, preventing a false pass caused by absent data. Real ownership fixtures cover aspirant/coder self-service stage visibility without staff history, including ignored include/expand/fields parameters.

Staff dossier, review/version history, decisions, execution history and audit remain denied to learner accounts. Foreign-program/anonymous errors must not echo canaries. Scoped administrative audit retains expected actions without copying internal text. Application-log checks cover successful writes/reads, denied reads and invalid-input validation. Authorized staff reads remain intact; no permissions are changed.

This does not implement future collaboration or certify all privacy/security requirements. Free-text sensitivity detection, retention, exports, AI prompts and unimplemented views are not covered. The broader AMP story remains subject to capacity/acceptance. No production code, schema, dependencies, seed or Jira changes.

## Evidence / Evidencia

Local ruff, compilation and whitespace checks PASS. PostgreSQL/Docker NOT RUN locally (unavailable); full current-head CI runs the real DB regressions and results are recorded in the PR. No new runtime assertion is inferred from this report. Review: Elizabeth primary per Jira; David secondary for leakage/log evidence. Independent of KAN-144; both can merge without stacking.
