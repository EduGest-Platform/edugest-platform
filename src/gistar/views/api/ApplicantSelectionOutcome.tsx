import { useEffect, useId, useState } from 'react'
import { api, type Schemas } from '../../../shared/api/client'
import { describeApiError, problemText } from '../../../shared/api/errors'
import { humanize } from '../../config'
import { Button, Notice, Status } from '../../ui'

type Outcome = Schemas['OwnSelectionOutcome']
type Result = { outcome: Outcome } | { error: string } | null

const decidedDate = new Intl.DateTimeFormat('es-ES', {
  dateStyle: 'long', timeStyle: 'short', timeZone: 'Europe/Madrid',
})

export function AppliedSelectionDecision({ outcome }: { outcome: Outcome }) {
  if (!outcome.outcome)
    return <p role="status" className="text-sm text-muted">
      {outcome.stage === 'retirada' ? 'Tu candidatura está retirada.' : 'Todavía no hay una decisión de selección disponible.'}
    </p>

  return (
    <div className="grid gap-2">
      <div className="flex flex-wrap items-center gap-2">
        <Status s={outcome.outcome} />
        {outcome.decided_at && <time className="text-xs text-muted" dateTime={outcome.decided_at}>
          {decidedDate.format(new Date(outcome.decided_at))}
        </time>}
      </div>
      {outcome.outcome === 'lista_espera' && (
        <p className="text-sm">Estás en lista de espera. Consulta este resultado si cambia tu situación.</p>
      )}
      {outcome.outcome === 'no_admitida' && (
        <p className="text-sm">No has obtenido una plaza en esta convocatoria. Puedes consultar otras convocatorias o contactar con el equipo de admisión.</p>
      )}
      {outcome.outcome === 'admitida' && (outcome.enrollment ? (
        <dl className="grid grid-cols-[auto_minmax(0,1fr)] gap-x-3 gap-y-1 text-sm">
          <dt className="font-medium">Cohorte</dt>
          <dd>{outcome.enrollment.cohort_id}</dd>
          <dt className="font-medium">Estado de matrícula</dt>
          <dd className="first-letter:uppercase">{humanize(outcome.enrollment.status)}</dd>
        </dl>
      ) : <p className="text-sm">La decisión de admisión está registrada. La matrícula todavía no está disponible en esta vista.</p>)}
    </div>
  )
}

function SelectionOutcomeDetails({ id }: { id: string }) {
  const [result, setResult] = useState<Result>(null)
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    void api.GET('/api/v1/me/applications/{application_id}/selection-outcome', {
      params: { path: { application_id: id } },
      signal: controller.signal,
    }).then(({ data, error, response }) => {
      if (controller.signal.aborted) return
      if (data?.application_id === id) setResult({ outcome: data })
      else setResult({ error: problemText(describeApiError(response.status, error)) })
    }).catch(() => {
      if (!controller.signal.aborted) setResult({ error: 'No se pudo conectar con el servidor. Vuelve a intentarlo.' })
    })
    return () => controller.abort()
  }, [id, attempt])

  return (
    <div className="grid gap-3">
      {!result ? <p role="status" className="text-sm text-muted">Cargando resultado de selección…</p>
        : 'error' in result ? <Notice tone="warning" live="assertive">{result.error}</Notice>
        : <AppliedSelectionDecision outcome={result.outcome} />}
      <Button className="justify-self-start" size="sm" variant="ghost" onClick={() => {
        setResult(null)
        setAttempt(value => value + 1)
      }}>Actualizar resultado</Button>
    </div>
  )
}

export function ApplicantSelectionOutcome({ id, code }: { id: string; code: string }) {
  const [open, setOpen] = useState(false)
  const detailsId = useId()

  return (
    <>
      <Button
        className="justify-self-start"
        size="sm"
        variant="ghost"
        aria-label={`${open ? 'Ocultar resultado' : 'Ver resultado'} de ${code}`}
        aria-expanded={open}
        aria-controls={detailsId}
        onClick={() => setOpen(value => !value)}
      >{open ? 'Ocultar resultado' : 'Ver resultado'}</Button>
      <div id={detailsId} hidden={!open} className="border-t border-line pt-3">
        {open && <SelectionOutcomeDetails id={id} />}
      </div>
    </>
  )
}
