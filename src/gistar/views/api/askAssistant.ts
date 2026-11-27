import { api } from '../../../shared/api/client'

export function askAssistant(question: string, signal: AbortSignal, cohortId?: string) {
  return api.POST('/api/v1/assistant/ask', {
    body: { question, cohort_id: cohortId?.trim() || null },
    signal,
  })
}

export function listAssistantCohorts(signal: AbortSignal) {
  return api.GET('/api/v1/cohorts', { signal })
}
