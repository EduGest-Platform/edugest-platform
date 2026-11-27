import { api, type Schemas } from './client'
import { describeApiError, problemText } from './errors'

export type AssistantSource = NonNullable<Schemas['AskOut']['source_kind']>

type Progress = {
  onPhase: (source: AssistantSource) => void
  onDelta: (text: string) => void
}

export class AssistantStreamError extends Error {}

export async function readAssistantStream(body: ReadableStream<Uint8Array>, progress: Progress): Promise<Schemas['AskOut']> {
  const reader = body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  try {
    while (true) {
      const { value, done } = await reader.read()
      buffer += decoder.decode(value, { stream: !done })
      for (let boundary = /\r?\n\r?\n/.exec(buffer); boundary; boundary = /\r?\n\r?\n/.exec(buffer)) {
        const lines = buffer.slice(0, boundary.index).split(/\r?\n/)
        buffer = buffer.slice(boundary.index + boundary[0].length)
        const event = lines.find(line => line.startsWith('event:'))?.slice(6).trim()
        const data = lines.filter(line => line.startsWith('data:')).map(line => line.slice(5).replace(/^ /, '')).join('\n')
        if (!data) continue

        if (event === 'error') throw new AssistantStreamError(problemText(describeApiError(500)))
        if (event !== 'phase' && event !== 'delta' && event !== 'answer') continue
        let payload: Record<string, unknown>
        try {
          const parsed: unknown = JSON.parse(data)
          if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) throw new Error('Invalid payload')
          payload = parsed as Record<string, unknown>
        } catch {
          throw new AssistantStreamError('La respuesta del asistente no es válida. Vuelve a intentarlo.')
        }
        switch (event) {
          case 'phase': {
            const source: unknown = payload.source_kind
            if (source === 'documents' || source === 'records') progress.onPhase(source)
            break
          }
          case 'delta': {
            const text: unknown = payload.text
            if (typeof text === 'string') progress.onDelta(text)
            break
          }
          case 'answer':
            if (typeof payload.answer !== 'string'
              || (payload.status !== 'answered' && payload.status !== 'no_source')
              || (payload.source_kind !== 'documents' && payload.source_kind !== 'records')
              || (payload.mode !== 'extractive' && payload.mode !== 'template')
              || (payload.retrieval !== null && payload.retrieval !== 'hybrid' && payload.retrieval !== 'keyword')
              || typeof payload.as_of !== 'string'
              || !Array.isArray(payload.citations)
              || !Array.isArray(payload.scope_cohorts)
              || !payload.scope_cohorts.every(cohort => typeof cohort === 'string')) {
              throw new AssistantStreamError('La respuesta del asistente no es válida. Vuelve a intentarlo.')
            }
            return payload as Schemas['AskOut']
        }
      }
      if (done) throw new AssistantStreamError('La conexión se cerró antes de recibir la respuesta completa. Vuelve a intentarlo.')
    }
  } finally {
    // The final event is sufficient. Release the connection even if the server has not closed it yet.
    void reader.cancel().catch(() => {})
    reader.releaseLock()
  }
}

export async function streamAssistant(
  body: Schemas['AskIn'], signal: AbortSignal, progress: Progress,
): Promise<Schemas['AskOut']> {
  const { data, error, response } = await api.POST('/api/v1/assistant/ask/stream', {
    body,
    signal,
    headers: { Accept: 'text/event-stream' },
    parseAs: 'stream',
  })
  if (!response.ok) throw new AssistantStreamError(problemText(describeApiError(response.status, error)))
  if (!data || !response.headers.get('content-type')?.startsWith('text/event-stream')) {
    throw new AssistantStreamError('No se pudo abrir la consulta del asistente. Vuelve a intentarlo.')
  }
  return readAssistantStream(data, progress)
}
