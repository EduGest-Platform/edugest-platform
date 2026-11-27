import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react'
import { api, type Schemas } from '../../../shared/api/client'
import { describeApiError, problemText } from '../../../shared/api/errors'
import { Button, Card, Field, Notice, inputCls } from '../../ui'
import { LearnerReadProblem, requireLearnerResponse, useLearnerRead } from './OwnEnrollmentPicker'

const dateTime = new Intl.DateTimeFormat('es-ES', { dateStyle: 'medium', timeStyle: 'short' })
type Action = 'save' | 'remove' | 'metadata'

const validRepository = (value: string) => /^https:\/\/github\.com\/[A-Za-z0-9-]+\/[A-Za-z0-9_.-]+\/?$/.test(value.trim()) && !value.trim().split('/').filter(Boolean).at(-1)?.includes('..')

export function LearnerPortfolio({ enrollmentId }: { enrollmentId: string }) {
  const load = useCallback(async (signal: AbortSignal) => requireLearnerResponse(
    await api.GET('/api/v1/me/enrollments/{enrollment_id}/portfolio', {
      params: { path: { enrollment_id: enrollmentId } }, signal,
    }),
  ), [enrollmentId])
  const { state, retry } = useLearnerRead(load)
  const [url, setUrl] = useState('')
  const [authorized, setAuthorized] = useState(false)
  const [metadata, setMetadata] = useState<Schemas['PublicRepository']>()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const pending = useRef<AbortController | null>(null)
  useEffect(() => () => pending.current?.abort(), [])

  async function perform(action: Action) {
    if (pending.current || (action === 'save' && (!authorized || !validRepository(url)))) return
    const controller = new AbortController()
    pending.current = controller
    setBusy(true)
    setError('')
    setNotice('')
    setMetadata(undefined)
    const params = { path: { enrollment_id: enrollmentId } }
    const signal = controller.signal
    try {
      if (action === 'metadata') {
        const data = requireLearnerResponse(await api.POST('/api/v1/me/enrollments/{enrollment_id}/portfolio/metadata', { params, signal }))
        if (!signal.aborted) setMetadata(data)
        return
      }
      if (action === 'save') {
        requireLearnerResponse(await api.PUT('/api/v1/me/enrollments/{enrollment_id}/portfolio', {
          params, body: { url: url.trim(), authorized: true }, signal,
        }))
      } else {
        const result = await api.DELETE('/api/v1/me/enrollments/{enrollment_id}/portfolio', { params, signal })
        if (!result.response.ok) throw new Error(problemText(describeApiError(result.response.status, result.error)))
      }
      if (signal.aborted) return
      setNotice(action === 'save' ? 'Enlace guardado.' : 'Enlace eliminado.')
      setUrl('')
      setAuthorized(false)
      retry()
    } catch (failure) {
      if (signal.aborted) return
      setError(failure instanceof Error && !(failure instanceof TypeError)
        ? failure.message : 'No se pudo confirmar la operación. Revisa la conexión e inténtalo de nuevo.')
    } finally {
      pending.current = null
      if (!signal.aborted) setBusy(false)
    }
  }

  const portfolio = state && 'data' in state ? state.data : undefined
  return (
    <Card title="Portfolio GitHub">
      <div className="grid gap-3">
        {!state && <p role="status">Cargando portfolio…</p>}
        {state && 'error' in state && <LearnerReadProblem message={state.error} retry={retry} />}
        {notice && <Notice live="polite">{notice}</Notice>}
        {error && <Notice tone="warning" live="assertive">{error}</Notice>}
        {portfolio && <>
          <p className="text-sm text-muted">El enlace queda visible solo en tu matrícula. Usa un repositorio público sintético o que tengas permiso para enlazar.</p>
          {portfolio.url ? <div className="grid gap-2">
            <a href={portfolio.url} target="_blank" rel="noopener noreferrer" className="break-all text-blue underline">{portfolio.url}</a>
            <div className="flex flex-wrap gap-2">
              {portfolio.can_lookup && <Button variant="ghost" size="sm" disabled={busy}
                onClick={() => void perform('metadata')}>Consultar actividad pública</Button>}
              <Button variant="ghost" size="sm" disabled={busy} onClick={() => {
                if (window.confirm('¿Quitar el enlace de esta matrícula?')) void perform('remove')
              }}>Quitar enlace</Button>
            </div>
          </div> : <p className="text-sm">Aún no has añadido un enlace.</p>}
          {metadata && <dl className="grid gap-2 text-sm">
            <div><dt className="font-semibold">Lenguaje principal</dt><dd>{metadata.primary_language ?? 'Sin dato'}</dd></div>
            <div><dt className="font-semibold">Último envío a GitHub</dt>
              <dd>{metadata.last_push_at ? dateTime.format(new Date(metadata.last_push_at)) : 'Sin dato'}</dd></div>
          </dl>}
          {portfolio.can_edit && <form className="grid max-w-lg gap-3" onSubmit={(event: FormEvent) => {
            event.preventDefault()
            if (validRepository(url) && authorized) void perform('save')
          }}>
            <Field label={portfolio.url ? 'Nuevo repositorio de GitHub' : 'Repositorio de GitHub'} htmlFor="portfolio-repository">
              <input id="portfolio-repository" className={inputCls} value={url} type="url" required maxLength={320}
                aria-invalid={Boolean(url.trim() && !validRepository(url))} aria-describedby="portfolio-url-hint"
                placeholder="https://github.com/organizacion/repositorio" disabled={busy} onChange={event => setUrl(event.target.value)} />
            </Field>
            <p id="portfolio-url-hint" className="text-xs text-muted">Introduce un enlace HTTPS directo al repositorio, sin parámetros ni subrutas.</p>
            <label className="flex items-start gap-2 text-sm">
              <input type="checkbox" required disabled={busy} checked={authorized} onChange={event => setAuthorized(event.target.checked)} />
              Tengo permiso para enlazar este repositorio público.
            </label>
            <Button type="submit" className="justify-self-start" disabled={busy || !validRepository(url) || !authorized}>
              {portfolio.url ? 'Cambiar enlace' : 'Guardar enlace'}
            </Button>
          </form>}
        </>}
      </div>
    </Card>
  )
}
