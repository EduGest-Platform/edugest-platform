import { api } from '../../../shared/api/client'

export function askAssistant(question: string, signal: AbortSignal) {
  return api.POST('/api/v1/assistant/ask', {
    body: { question, cohort_id: null },
    signal,
  })
}
