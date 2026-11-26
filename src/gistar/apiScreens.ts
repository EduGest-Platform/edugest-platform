import type { ReactElement } from 'react'
import type { View } from './types'
import { ApiRiskAlerts } from './views/api/ApiRiskAlerts'
import { ApiCoordinationDashboard } from './views/api/ApiCoordinationDashboard'
import { ApiCohorts } from './views/api/ApiCohorts'
import { ApiCohortOverview } from './views/api/ApiCohortOverview'
import { ApiAttendance } from './views/api/ApiAttendance'
import { ApiAssistant } from './views/api/ApiAssistant'
import { ApiLearnerProgress } from './views/api/ApiLearnerProgress'
import { ApiLearnerDeliveries } from './views/api/ApiLearnerDeliveries'
import { ApiApplications, ApiAudit, ApiInscription, ApiMyApplications } from './views/api/ApiAdmissions'

/**
 * Screens that read/write the FastAPI backend in API mode.
 * Must list exactly the views in API_VIEWS (src/shared/api/config.ts); a test keeps both in sync.
 */
export const API_SCREENS: Partial<Record<View, () => ReactElement>> = {
  dashboard: ApiCoordinationDashboard,
  cohortes: ApiCohorts,
  analitica: ApiCohortOverview,
  asistencia: ApiAttendance,
  alertas: ApiRiskAlerts,
  asistente: ApiAssistant,
  progreso: ApiLearnerProgress,
  entregas: ApiLearnerDeliveries,
  inscripcion: ApiInscription,
  candidatura: ApiMyApplications,
  candidaturas: ApiApplications,
  auditoria: ApiAudit,
}
