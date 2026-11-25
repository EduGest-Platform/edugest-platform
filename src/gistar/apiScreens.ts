import type { ReactElement } from 'react'
import type { View } from './types'
import { ApiCohorts } from './views/api/ApiCohorts'
import { ApiCohortOverview } from './views/api/ApiCohortOverview'
import { ApiAttendance } from './views/api/ApiAttendance'
import { ApiAssistant } from './views/api/ApiAssistant'
import { ApiLearnerProgress } from './views/api/ApiLearnerProgress'
import { ApiApplications, ApiAudit, ApiInscription, ApiMyApplications } from './views/api/ApiAdmissions'

/**
 * Screens that read/write the FastAPI backend in API mode.
 * Must list exactly the views in API_VIEWS (src/shared/api/config.ts); a test keeps both in sync.
 */
export const API_SCREENS: Partial<Record<View, () => ReactElement>> = {
  cohortes: ApiCohorts,
  analitica: ApiCohortOverview,
  asistencia: ApiAttendance,
  asistente: ApiAssistant,
  progreso: ApiLearnerProgress,
  inscripcion: ApiInscription,
  candidatura: ApiMyApplications,
  candidaturas: ApiApplications,
  auditoria: ApiAudit,
}
