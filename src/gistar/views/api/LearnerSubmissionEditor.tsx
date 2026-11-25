import { useId, useRef, useState, type FormEvent } from 'react'
import { api } from '../../../shared/api/client'
import { describeApiError, problemText } from '../../../shared/api/errors'
import { Button, Field, Notice, inputCls } from '../../ui'
import type { LearnerDelivery } from './learnerDeliveryStates'
import { PORTFOLIO_LINK_MAX_LENGTH, validPortfolioLink } from './portfolioLink'

export function LearnerSubmissionDraft({ link, message, onClose }: {
  link: string
  message: string
  onClose: () => void
}) {
  const fieldId = useId()
  return (
    <div className="mt-3 grid justify-items-start gap-3">
      <Notice live="polite">{message} Puedes copiar el enlace del borrador.</Notice>
      <Field label="Enlace del borrador" htmlFor={fieldId}>
        <input id={fieldId} type="text" className={inputCls} value={link} readOnly />
      </Field>
      <Button size="sm" variant="ghost" onClick={onClose}>Cerrar borrador</Button>
    </div>
  )
}

export function LearnerSubmissionEditor({ item, enrollmentId, link, onLinkChange, onCancel, onSaved, onRefresh }: {
  item: LearnerDelivery
  enrollmentId: string
  link: string
  onLinkChange: (link: string) => void
  onCancel: () => void
  onSaved: () => void
  onRefresh: () => void
}) {
  const fieldId = useId()
  const submitting = useRef(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<{ message: string; refresh?: boolean } | null>(null)

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (submitting.current || item.reviewed || error?.refresh) return
    const text = link.trim()
    const portfolio = text ? validPortfolioLink(text) : null
    if (text && !portfolio) {
      setError({ message: 'Introduce un enlace HTTPS válido sin credenciales.' })
      return
    }

    submitting.current = true
    setBusy(true)
    setError(null)
    try {
      const { data, response, error: problem } = await api.PUT('/api/v1/assignments/{assignment_id}/submissions/{enrollment_id}', {
        params: { path: { assignment_id: item.assignment_id, enrollment_id: enrollmentId } },
        body: { portfolio_url: portfolio },
      })
      if (data) onSaved()
      else setError({ message: problemText(describeApiError(response.status, problem)), refresh: response.status === 409 })
    } catch {
      setError({ message: 'No se pudo confirmar el envío. Actualiza la actividad para comprobar si se guardó.', refresh: true })
    } finally {
      submitting.current = false
      setBusy(false)
    }
  }

  return (
    <form className="mt-3 grid justify-items-start gap-3" onSubmit={submit} noValidate>
      <div className="w-full max-w-lg">
        <Field label="Enlace del portfolio (opcional)" htmlFor={fieldId}>
          <input id={fieldId} type="url" className={inputCls} value={link} maxLength={PORTFOLIO_LINK_MAX_LENGTH}
            disabled={busy} aria-describedby={error ? fieldId + '-error' : undefined}
            onChange={event => {
              onLinkChange(event.target.value)
              if (!error?.refresh) setError(null)
            }} />
        </Field>
      </div>
      {error && <div id={fieldId + '-error'}><Notice tone="warning" live="polite">{error.message}</Notice></div>}
      <div className="flex flex-wrap gap-2">
        <Button size="sm" type="submit" disabled={busy || error?.refresh}>
          {item.submission ? 'Guardar reentrega' : 'Guardar entrega'}
        </Button>
        <Button size="sm" variant="ghost" disabled={busy} onClick={onCancel}>Cancelar</Button>
        {error?.refresh && <Button size="sm" variant="ghost" disabled={busy} onClick={onRefresh}>Actualizar actividad</Button>}
      </div>
    </form>
  )
}
