/**
 * Data source switch. Without VITE_GISTAR_API_URL the prototype runs exactly as before (local, localStorage).
 * With it, inscription, applications/CRM and audit use the FastAPI backend; other views remain local until migrated.
 */
export const API_URL: string | undefined = import.meta.env.VITE_GISTAR_API_URL?.replace(/\/$/, '') || undefined
export const API_MODE = !!API_URL

/** Views whose data already comes from the API in API mode (increment F1). */
export const API_VIEWS = new Set(['inscripcion', 'candidatura', 'candidaturas', 'auditoria'])
