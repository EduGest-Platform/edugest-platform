import { useEffect, useState } from 'react'
import { api, errorMessage, type Schemas } from '../../../shared/api/client'
import { Button, Notice } from '../../ui'

function Feedback({ submissionId }: { submissionId: string }) {
  const [data, setData] = useState<Schemas['PublishedFeedback']>()
  const [error, setError] = useState('')
  const [attempt, setAttempt] = useState(0)
  useEffect(() => {
    setData(undefined)
    setError('')
    const controller = new AbortController()
    void api.GET('/api/v1/submissions/{submission_id}/feedback', {
      params: { path: { submission_id: submissionId } }, signal: controller.signal,
    }).then(result => {
      if (controller.signal.aborted) return
      if (result.data) setData(result.data)
      else setError(errorMessage(result.error, 'No se pudo consultar el feedback.'))
    }).catch(() => {
      if (!controller.signal.aborted) setError('No se pudo conectar con el servidor.')
    })
    return () => controller.abort()
  }, [submissionId, attempt])
  return (
    <div className="mt-2 grid gap-2">
      {!data && !error && <p role="status">Cargando feedback…</p>}
      {error && <Notice tone="warning" live="assertive">{error}</Notice>}
      {data && (data.feedback ? <>
        <p className="font-medium">{data.feedback.label} · Versión {data.feedback.version}</p>
        <p className="whitespace-pre-wrap wrap-anywhere">{data.feedback.body}</p>
      </> : <p>Todavía no hay feedback publicado.</p>)}
      <Button variant="ghost" size="sm" className="justify-self-start"
        onClick={() => setAttempt(value => value + 1)}>Actualizar feedback</Button>
    </div>
  )
}

export function PublishedDeliveryFeedback({ submissionId }: { submissionId: string }) {
  const [open, setOpen] = useState(false)
  return (
    <details className="rounded-xl border border-line p-3 text-sm" onToggle={event => setOpen(event.currentTarget.open)}>
      <summary className="cursor-pointer font-semibold">Feedback de la entrega</summary>
      {open && <Feedback submissionId={submissionId} />}
    </details>
  )
}
