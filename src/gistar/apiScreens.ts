import type { ReactElement } from 'react'
import type { View } from './types'
import { ApiCohorts } from './views/api/ApiCohorts'
import { ApiAttendance } from './views/api/ApiAttendance'
import { ApiAssistant } from './views/api/ApiAssistant'
import { ApiApplications, ApiAudit, ApiInscription, ApiMyApplications } from './views/api/ApiAdmissions'

/**
 * Screens that read/write the FastAPI backend in API mode.
 * Must list exactly the views in API_VIEWS (src/shared/api/config.ts); a test keeps both in sync.
 */
export const API_SCREENS: Partial<Record<View, () => ReactElement>> = {
  cohortes: ApiCohorts,
  asistencia: ApiAttendance,
  asistente: ApiAssistant,
  inscripcion: ApiInscription,
  candidatura: ApiMyApplications,
  candidaturas: ApiApplications,
  auditoria: ApiAudit,
}
