/**
 * Data source switch. Without VITE_GISTAR_API_URL the prototype runs exactly as before (local, localStorage).
 * With it, inscription, applications/CRM and audit use the FastAPI backend; other views remain local until migrated.
 */
export const API_URL: string | undefined = import.meta.env.VITE_GISTAR_API_URL?.replace(/\/$/, '') || undefined
export const API_MODE = !!API_URL

/** Views whose data already comes from the API in API mode (increment F1). */
export const API_VIEWS = new Set(['inscripcion', 'candidatura', 'candidaturas', 'auditoria', 'cohortes', 'asistencia', 'asistente', 'progreso', 'analitica'])

export type DataSource = 'api' | 'local'

/**
 * Where a view reads and writes its data. Local mode: every view is local (localStorage).
 * API mode: only the migrated views in API_VIEWS use the API; a view never mixes both sources (ADR-0004).
 */
export function dataSourceFor(view: string, apiMode: boolean = API_MODE): DataSource {
  return apiMode && API_VIEWS.has(view) ? 'api' : 'local'
}
