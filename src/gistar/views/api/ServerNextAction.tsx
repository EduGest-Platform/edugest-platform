import { useCallback, useEffect, useState } from 'react'
import { api, type Schemas } from '../../../shared/api/client'
import { describeApiError, problemText } from '../../../shared/api/errors'
import { formatDueDate, teamToday, type NextActionDraft } from '../../nextAction'
import { Button, Field, Notice, inputCls } from '../../ui'

export function NextActionSummary({ action, label = 'Próxima acción' }: { action: Schemas['NextActionOut']; label?: string }) {
  return (
    <p className="mt-1">
      <b className="font-semibold">{label}:</b> {action.description} · Responsable: {action.owner} · Plazo: {formatDueDate(action.due_on)}
    </p>
  )
}

export type CrmOwners = { items: Schemas['CrmOwnerOut'][]; loading: boolean; error: string | null; reload: () => void }

/** Lives in the dossier, so the list survives switching the event type back and forth. */
export function useCrmOwners(applicationId: string): CrmOwners {
  const [items, setItems] = useState<Schemas['CrmOwnerOut'][]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    async function loadOwners() {
      setLoading(true)
      try {
        const { data, error: apiError, response } = await api.GET('/api/v1/applications/{application_id}/crm-owners', {
          signal: controller.signal,
          params: { path: { application_id: applicationId } },
        })
        if (controller.signal.aborted) return
        setItems(data ?? [])
        setError(data ? null : problemText(describeApiError(response.status, apiError)))
      } catch {
        if (controller.signal.aborted) return
        setItems([])
        setError('No se pudo cargar la lista de responsables. Revisa tu conexión.')
      }
      setLoading(false)
    }
    void loadOwners()
    return () => controller.abort()
  }, [applicationId, attempt])

  const reload = useCallback(() => setAttempt((previous) => previous + 1), [])
  return { items, loading, error, reload }
}

type NextActionFieldsProps = {
  owners: CrmOwners
  value: NextActionDraft
  problem: string | null
  disabled: boolean
  onChange: (draft: NextActionDraft) => void
}

/** Optional fields of a contact. It only records the commitment: nothing is sent to anyone. */
export function NextActionFields({ owners, value, problem, disabled, onChange }: NextActionFieldsProps) {
  const selected = owners.items.some((owner) => owner.user_id === value.owner_user_id) ? value.owner_user_id : ''

  return (
    <fieldset className="grid gap-2" disabled={disabled} aria-describedby="next-action-help">
      <legend className="mb-1 text-[13px] font-semibold">Próxima acción (opcional: si la indicas, completa los tres campos)</legend>
      {owners.error && (
        <div className="grid justify-items-start gap-2">
          <Notice tone="warning" live="assertive">{owners.error}</Notice>
          <Button type="button" size="sm" variant="ghost" onClick={owners.reload}>Volver a cargar responsables</Button>
        </div>
      )}
      <Field label="Qué hay que hacer" htmlFor="next-action-text" hint="Sin datos de salud ni situación personal.">
        <input id="next-action-text" className={inputCls} maxLength={200} value={value.description} onChange={(e) => onChange({ ...value, description: e.target.value })} />
      </Field>
      <div className="grid gap-2 sm:grid-cols-2">
        <Field label="Persona responsable" htmlFor="next-action-owner">
          <select id="next-action-owner" className={inputCls} value={selected} onChange={(e) => onChange({ ...value, owner_user_id: e.target.value })}>
            <option value="">{owners.loading ? 'Cargando…' : 'Sin asignar'}</option>
            {owners.items.map((owner) => <option key={owner.user_id} value={owner.user_id}>{owner.display_name}</option>)}
          </select>
        </Field>
        <Field label="Plazo" htmlFor="next-action-due">
          <input id="next-action-due" type="date" className={inputCls} min={teamToday()} value={value.due_on} onChange={(e) => onChange({ ...value, due_on: e.target.value })} />
        </Field>
      </div>
      {/* Always mounted, so screen readers announce the text when it appears. */}
      <p id="next-action-help" role="status" className="text-xs text-muted">{problem}</p>
    </fieldset>
  )
}
