import { useEffect, useRef, useState, type FormEvent } from 'react'
import { api, type Schemas } from '../../../shared/api/client'
import { describeApiError, problemText } from '../../../shared/api/errors'
import { Modal } from '../../components/Modal'
import { Button, Field, Notice, inputCls } from '../../ui'

type QueueItem = Schemas['FeedbackQueueItem']
type Draft = Schemas['FeedbackDraftOut']
type ResponseData = { data?: Draft; error?: unknown; response: Response }

export function FeedbackReviewModal({ item, onClose }: { item: QueueItem; onClose: () => void }) {
  const [versions, setVersions] = useState<Schemas['FeedbackDraftList']>()
  const [attempt, setAttempt] = useState(0)
  const [edit, setEdit] = useState<{ id: string; version: number; body: string } | null>(null)
  const [confirmedVersion, setConfirmedVersion] = useState<string | null>(null)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [busy, setBusy] = useState(false)
  const [uncertain, setUncertain] = useState(false)
  const pending = useRef<AbortController | null>(null)

  useEffect(() => () => pending.current?.abort(), [])
  useEffect(() => {
    const controller = new AbortController()
    void api.GET('/api/v1/submissions/{submission_id}/feedback-drafts', {
      params: { path: { submission_id: item.submission_id } }, signal: controller.signal,
    }).then(result => {
      if (controller.signal.aborted) return
      if (result.data) {
        setVersions(result.data)
        setUncertain(false)
      }
      else setError(problemText(describeApiError(result.response.status, result.error)))
    }).catch(() => {
      if (!controller.signal.aborted) setError('No se pudieron cargar las versiones del feedback.')
    })
    return () => controller.abort()
  }, [item.submission_id, attempt])

  function reload() {
    setVersions(undefined)
    setError('')
    setConfirmedVersion(null)
    setAttempt(value => value + 1)
  }

  async function write(send: (signal: AbortSignal) => Promise<ResponseData>, message: string) {
    if (pending.current || uncertain || !versions) return
    const controller = new AbortController()
    pending.current = controller
    setBusy(true)
    setNotice('')
    setError('')
    try {
      const result = await send(controller.signal)
      if (controller.signal.aborted) return
      if (result.data) {
        setEdit(null)
        setNotice(message)
        reload()
      } else {
        if (result.response.status >= 500 || result.response.status === 408 || result.response.status === 409) {
          setUncertain(true)
          setConfirmedVersion(null)
        }
        setError(problemText(describeApiError(result.response.status, result.error)))
      }
    } catch {
      if (!controller.signal.aborted) {
        setUncertain(true)
        setConfirmedVersion(null)
        setError('No se pudo confirmar el cambio. Actualiza las versiones antes de reintentar.')
      }
    } finally {
      pending.current = null
      if (!controller.signal.aborted) setBusy(false)
    }
  }

  const latest = versions?.items.at(-1)
  const current = latest?.submission_revision === versions?.current_revision
  const publishable = latest?.status === 'draft' && current && !edit

  function saveEdit(event: FormEvent) {
    event.preventDefault()
    if (!edit || latest?.id !== edit.id || !current || !edit.body.trim()) return
    void write(signal => api.PUT('/api/v1/feedback-drafts/{draft_id}', {
      params: { path: { draft_id: edit.id } }, body: { body: edit.body, expected_version: edit.version }, signal,
    }), 'Se guardó una nueva versión del borrador.')
  }

  return (
    <Modal open onClose={onClose} dirty={Boolean(edit || confirmedVersion || busy)} title="Revisar feedback"
      subtitle={`${item.assignment_title} · ${item.learner_name}`} placement="end">
      <div className="grid gap-4">
        {notice && <Notice live="polite">{notice}</Notice>}
        {error && <Notice tone="warning" live="assertive">{error}</Notice>}
        {uncertain && <Notice tone="warning">Comprueba las versiones actualizadas antes de realizar otra operación.</Notice>}
        <Button variant="ghost" className="justify-self-start" onClick={reload} disabled={busy}>Actualizar versiones</Button>
        {!versions && !error && <p role="status">Cargando versiones…</p>}
        {versions && <>
          <p className="text-sm text-muted">Revisión actual de la entrega: {versions.current_revision}.</p>
          <div className="flex flex-wrap gap-2">
            <Button disabled={busy || uncertain || Boolean(edit)} onClick={() => void write(signal =>
              api.POST('/api/v1/submissions/{submission_id}/feedback-drafts', {
                params: { path: { submission_id: item.submission_id } }, signal,
              }), 'Borrador generado.')}>Generar borrador</Button>
            {latest?.status === 'draft' && current && !edit && (
              <Button variant="ghost" disabled={busy} onClick={() => {
                setConfirmedVersion(null)
                setEdit({ id: latest.id, version: latest.version, body: latest.body })
              }}>Editar borrador</Button>
            )}
          </div>
          {latest && <>
            <article className="rounded-xl border border-line p-3">
              <h3 className="font-semibold">Versión {latest.version} · {latest.status === 'approved' ? 'Publicada' : 'Borrador'}</h3>
              <p className="text-sm text-muted">{latest.label}</p>
              {!current && <p className="text-sm">Corresponde a la revisión {latest.submission_revision}. Genera un borrador de la revisión actual para publicar.</p>}
              <p className="mt-3 whitespace-pre-wrap wrap-anywhere text-sm">{latest.body}</p>
            </article>
            {publishable && <div className="grid gap-2 rounded-xl bg-mist p-3">
              <label className="flex items-start gap-2 text-sm">
                <input type="checkbox" disabled={busy || uncertain} checked={confirmedVersion === latest.id}
                  onChange={event => setConfirmedVersion(event.target.checked ? latest.id : null)} />
                He revisado la versión {latest.version} y autorizo que el alumno vea este feedback.
              </label>
              <Button className="justify-self-start" disabled={busy || uncertain || confirmedVersion !== latest.id} onClick={() =>
                void write(signal => api.POST('/api/v1/feedback-drafts/{draft_id}/approve', {
                  params: { path: { draft_id: latest.id } },
                  body: { expected_revision: versions.current_revision }, signal,
                }), 'Feedback publicado para el alumno.')}>Aprobar y publicar</Button>
            </div>}
            {versions.items.length > 1 && <details className="rounded-xl border border-line p-3">
              <summary className="cursor-pointer font-medium">Versiones anteriores</summary>
              <ol className="mt-2 grid gap-2">
                {versions.items.slice(0, -1).reverse().map(draft => <li key={draft.id} className="border-b border-line py-2 text-sm">
                  <p className="font-medium">Versión {draft.version} · Entrega {draft.submission_revision} · {draft.status === 'approved' ? 'Publicada' : 'Borrador'}</p>
                  <p className="whitespace-pre-wrap wrap-anywhere">{draft.body}</p>
                </li>)}
              </ol>
            </details>}
          </>}
          {!latest && <p className="text-sm text-muted">Todavía no hay borradores para esta entrega.</p>}
        </>}
        {edit && <form className="grid gap-2" onSubmit={saveEdit}>
          <Field label="Texto revisado" htmlFor="feedback-edit-body">
            <textarea id="feedback-edit-body" className={inputCls} value={edit.body} required maxLength={4000} rows={7}
              readOnly={busy} onChange={event => setEdit({ ...edit, body: event.target.value })} />
          </Field>
          {versions && (edit.id !== latest?.id || !current) && <Notice tone="warning">
            La versión disponible cambió. Puedes copiar tu texto; vuelve a abrir el borrador actual antes de editarlo.
          </Notice>}
          <div className="flex flex-wrap gap-2">
            <Button type="submit" disabled={busy || uncertain || edit.id !== latest?.id || !current || !edit.body.trim()}>Guardar versión</Button>
            <Button variant="ghost" disabled={busy} onClick={() => setEdit(null)}>Descartar edición</Button>
          </div>
        </form>}
      </div>
    </Modal>
  )
}
