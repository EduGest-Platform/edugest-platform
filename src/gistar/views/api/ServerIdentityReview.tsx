import { useCallback, useEffect, useState } from 'react'
import { api, type Schemas } from '../../../shared/api/client'
import { describeApiError, problemText } from '../../../shared/api/errors'
import { DIFFERENT_PERSON, emptyIdentityDraft, identityBlockerText, identityDecision, isIdentityDraftDirty, type IdentityDraft } from '../../identityReview'
import { useGistar } from '../../store'
import { Button, Field, Notice, Status, inputCls } from '../../ui'

type Review = Schemas['IdentityReviewOut']
type Match = Schemas['IdentityMatch']

const PATH = '/api/v1/applications/{application_id}/identity-review'
const decidedAt = (iso: string) => new Intl.DateTimeFormat('es-ES', { dateStyle: 'medium', timeStyle: 'short', timeZone: 'Europe/Madrid' }).format(new Date(iso))

type Props = {
  applicationId: string
  onDirty: (dirty: boolean) => void
  /** The decision can change whose dossier this is, so the dossier and the list reload. */
  onResolved: () => void
}

/** KAN-274: nothing is linked until a person decides here. The server keeps who decided, when and why. */
export function ServerIdentityReview({ applicationId, onDirty, onResolved }: Props) {
  const { toast } = useGistar()
  const [review, setReview] = useState<Review | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [draft, setDraft] = useState<IdentityDraft>(emptyIdentityDraft)
  const [busy, setBusy] = useState(false)

  const load = useCallback(async () => {
    try {
      const { data, error: apiError, response } = await api.GET(PATH, { params: { path: { application_id: applicationId } } })
      setReview(data ?? null)
      setError(data ? null : problemText(describeApiError(response.status, apiError)))
    } catch {
      setError('No se pudo comprobar si hay un posible duplicado. Revisa tu conexión.')
    }
  }, [applicationId])

  useEffect(() => {
    void load()
  }, [load])

  const dirty = review?.status === 'pendiente' && isIdentityDraftDirty(draft)
  useEffect(() => {
    onDirty(dirty)
    return () => onDirty(false)
  }, [dirty, onDirty])

  const submit = async (body: Schemas['IdentityDecisionCreate']) => {
    setBusy(true)
    let result
    try {
      result = await api.POST(PATH, { params: { path: { application_id: applicationId } }, body })
    } catch {
      // The server may have saved it before the connection dropped.
      void load()
      return toast('No se pudo confirmar la decisión. Comprueba el aviso antes de repetirla.')
    } finally {
      setBusy(false)
    }
    if (!result.data) {
      // Someone else may have decided, or the matches may have changed.
      void load()
      return toast(problemText(describeApiError(result.response.status, result.error)))
    }
    setReview(result.data)
    setDraft(emptyIdentityDraft)
    toast('Decisión de duplicado registrada')
    onResolved()
  }

  if (error) {
    return (
      <div className="grid justify-items-start gap-2">
        <Notice tone="warning" live="assertive">{error}</Notice>
        <Button size="sm" variant="ghost" onClick={() => void load()}>Volver a comprobar duplicados</Button>
      </div>
    )
  }
  if (!review || review.status === 'sin_coincidencias') return null
  if (review.status !== 'pendiente') return <DecidedReview review={review} />

  const matches = review.matches ?? []
  const blockerText = identityBlockerText(review.blocker)
  const decision = identityDecision(draft, matches.map((match) => match.person_id))

  return (
    <section aria-labelledby="identity-review-title" className="grid gap-3 rounded-xl border border-amber-200 bg-amber-50/70 p-3">
      <div>
        <h3 id="identity-review-title" className="font-semibold">Posible duplicado sin resolver</h3>
        <p className="mt-1">El correo de esta inscripción ya figura en otro registro. No se une nada hasta que una persona lo decida, y mientras tanto no se puede admitir.</p>
        <p className="mt-1 text-muted">Nombre escrito en esta inscripción: {review.submitted_name}</p>
      </div>
      {matches.length > 0 && <MatchList matches={matches} />}
      {blockerText ? (
        <p role="status" className="font-medium">{blockerText}</p>
      ) : (
        <fieldset className="grid gap-2" disabled={busy}>
          <legend className="mb-1 text-[13px] font-semibold">Tu decisión (no se puede deshacer desde esta pantalla)</legend>
          {matches.map((match) => (
            <Choice key={match.person_id} value={match.person_id} draft={draft} onChange={setDraft}>
              Es la misma persona que {match.display_name}{match.applications.length > 0 && ` (${match.applications.map((a) => a.codigo).join(', ')})`}
            </Choice>
          ))}
          <Choice value={DIFFERENT_PERSON} draft={draft} onChange={setDraft}>Son personas distintas</Choice>
          <p className="text-muted">Si es la misma persona, este expediente pasará a mostrar el nombre del registro anterior, también al equipo de esta convocatoria.</p>
          <Field label="Motivo de la decisión" htmlFor="identity-reason" hint="Cómo lo has comprobado. Sin datos de salud ni situación personal.">
            <textarea id="identity-reason" maxLength={500} className={`${inputCls} min-h-16`} value={draft.reason} onChange={(e) => setDraft({ ...draft, reason: e.target.value })} />
          </Field>
          <div>
            <Button size="sm" disabled={busy || !decision} onClick={() => decision && void submit(decision)}>Registrar decisión</Button>
          </div>
        </fieldset>
      )}
    </section>
  )
}

function MatchList({ matches }: { matches: Match[] }) {
  return (
    <ul className="grid gap-2" aria-label="Registros con el mismo correo">
      {matches.map((match) => (
        <li key={match.person_id} className="rounded-lg border border-line bg-white px-3 py-2">
          <p className="font-semibold">{match.display_name}</p>
          {match.applications.length === 0 && <p className="text-muted">Registro sin candidaturas.</p>}
          {match.applications.map((a) => (
            <p key={a.application_id} className="mt-1 flex flex-wrap items-center gap-2">
              {a.codigo} · {a.call_id} <Status s={a.stage} />
            </p>
          ))}
        </li>
      ))}
    </ul>
  )
}

type ChoiceProps = { value: string; draft: IdentityDraft; onChange: (draft: IdentityDraft) => void; children: React.ReactNode }

function Choice({ value, draft, onChange, children }: ChoiceProps) {
  return (
    <label className="flex items-start gap-2">
      <input type="radio" name="identity-choice" className="mt-1" checked={draft.choice === value} onChange={() => onChange({ ...draft, choice: value })} />
      <span>{children}</span>
    </label>
  )
}

function DecidedReview({ review }: { review: Review }) {
  return (
    <div className="rounded-lg border border-line px-3 py-2">
      <p>
        <b className="font-semibold">Revisión de duplicado:</b> {review.status === 'misma_persona' ? 'misma persona' : 'personas distintas'}
        {review.decided_at && ` · ${review.decided_by} · ${decidedAt(review.decided_at)}`}
      </p>
      <p className="mt-1">Motivo: {review.reason ?? 'solo lo ve quien tiene acceso a todas las convocatorias implicadas.'}</p>
      <p className="mt-1 text-muted">Nombre escrito en esta inscripción: {review.submitted_name}</p>
    </div>
  )
}
