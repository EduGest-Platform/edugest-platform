import { useEffect, useRef, useState, type FormEvent } from 'react'
import { api, type Schemas } from '../../../shared/api/client'
import { describeApiError, problemText } from '../../../shared/api/errors'
import type { Me } from '../../../shared/api/session'
import { Modal } from '../../components/Modal'
import { Button, Field, Notice, inputCls } from '../../ui'

type Profile = Schemas['StaffProfileOut']
type AccessRequest = Schemas['AccessRequestOut']
type RequestInput = Schemas['AccessRequestCreate']
type Result<T> = { data?: T; error?: unknown; response: Response }

const PAGE_SIZE = 20
const roles = { admin: 'Administración', captacion: 'Captación', seleccion: 'Selección', docente: 'Docencia', coordinacion: 'Coordinación' }
const scopes = { global: 'Global', program: 'Programa', call: 'Convocatoria', cohort: 'Cohorte' }
const states: Record<string, string> = {
  requested: 'Pendiente de revisión', approved: 'Aprobada, pendiente de aplicación', rejected: 'Rechazada',
  applied: 'Aplicada', revoked: 'Revocada',
}
const dateTime = new Intl.DateTimeFormat('es-ES', { dateStyle: 'medium', timeStyle: 'short', timeZone: 'Europe/Madrid' })

function requestProblem(result: Result<unknown>) {
  return problemText(describeApiError(result.response.status, result.error))
}

export function StaffAccessPanel({ me, onClose }: { me: Me; onClose: () => void }) {
  const canReview = me.roles.some(role => role.role === 'admin' && role.scope_type === 'global')
  const [profile, setProfile] = useState<Profile | null>()
  const [profileError, setProfileError] = useState('')
  const [queue, setQueue] = useState<Schemas['AccessRequestList']>()
  const [queueError, setQueueError] = useState('')
  const [offset, setOffset] = useState(0)
  const [pendingOnly, setPendingOnly] = useState(true)
  const [attempt, setAttempt] = useState(0)
  const [token, setToken] = useState('')
  const [role, setRole] = useState<RequestInput['requested_role']>('docente')
  const [scope, setScope] = useState<RequestInput['scope_type']>('cohort')
  const [scopeId, setScopeId] = useState('')
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const pending = useRef<AbortController | null>(null)

  useEffect(() => () => pending.current?.abort(), [])
  useEffect(() => {
    const controller = new AbortController()
    setProfile(undefined)
    setProfileError('')
    void api.GET('/api/v1/staff/me', { signal: controller.signal }).then(result => {
      if (controller.signal.aborted) return
      if (result.data) setProfile(result.data)
      else if (result.response.status === 404) setProfile(null)
      else setProfileError(requestProblem(result))
    }).catch(() => {
      if (!controller.signal.aborted) setProfileError('No se pudo cargar la ficha interna.')
    })
    return () => controller.abort()
  }, [attempt])

  useEffect(() => {
    setQueue(undefined)
    setQueueError('')
    if (!canReview && profile?.state !== 'active') return
    const controller = new AbortController()
    void api.GET('/api/v1/staff/access-requests', {
      params: { query: { limit: PAGE_SIZE, offset, pending_only: canReview && pendingOnly } }, signal: controller.signal,
    }).then(result => {
      if (controller.signal.aborted) return
      if (result.data) setQueue(result.data)
      else setQueueError(requestProblem(result))
    }).catch(() => {
      if (!controller.signal.aborted) setQueueError('No se pudo cargar la cola de solicitudes.')
    })
    return () => controller.abort()
  }, [canReview, profile?.state, offset, attempt, pendingOnly])

  async function write(send: (signal: AbortSignal) => Promise<Result<unknown>>, onSuccess: () => void) {
    if (pending.current) return
    const controller = new AbortController()
    pending.current = controller
    setBusy(true)
    setError('')
    setNotice('')
    try {
      const result = await send(controller.signal)
      if (controller.signal.aborted) return
      if (result.data) {
        onSuccess()
        setAttempt(value => value + 1)
      } else setError(requestProblem(result))
    } catch {
      if (!controller.signal.aborted) setError('No se pudo confirmar el cambio. Actualiza antes de volver a intentarlo.')
    } finally {
      pending.current = null
      if (!controller.signal.aborted) setBusy(false)
    }
  }

  function accept(event: FormEvent) {
    event.preventDefault()
    const submitted = token.trim()
    setToken('')
    void write(signal => api.POST('/api/v1/staff/invitations/accept', { body: { token: submitted }, signal }),
      () => setNotice('Invitación aceptada. Ya puedes consultar tu ficha interna.'))
  }

  function requestAccess(event: FormEvent) {
    event.preventDefault()
    if (profile?.state !== 'active' || (scope !== 'global' && !scopeId.trim())) return
    void write(signal => api.POST('/api/v1/staff/access-requests', {
      body: { requested_role: role, scope_type: scope, scope_id: scope === 'global' ? null : scopeId.trim() }, signal,
    }), () => {
      setScopeId('')
      setNotice('Solicitud registrada y pendiente de revisión.')
    })
  }

  function review(request: AccessRequest, approved: boolean) {
    if (!canReview || request.requested_by === me.id || request.state !== 'requested') return
    void write(signal => api.POST('/api/v1/staff/access-requests/{request_id}/review', {
      params: { path: { request_id: request.id } }, body: { approved }, signal,
    }), () => setNotice(approved ? 'Solicitud aprobada. La aplicación del permiso sigue pendiente.' : 'Solicitud rechazada.'))
  }

  return (
    <Modal open onClose={onClose} placement="end" size="md" title="Personal y accesos"
      dirty={Boolean(token || scopeId || busy)}
      subtitle="Ficha interna y solicitudes de cambio de acceso.">
      <div className="grid gap-5">
        {notice && <Notice live="polite">{notice}</Notice>}
        {error && <Notice live="assertive" tone="warning">{error}</Notice>}
        <section className="grid gap-3" aria-label="Ficha interna">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h3 className="font-semibold">Mi ficha interna</h3>
            <Button size="sm" variant="ghost" disabled={busy} onClick={() => setAttempt(value => value + 1)}>Actualizar personal</Button>
          </div>
          {profileError && <Notice tone="warning" live="assertive">{profileError}</Notice>}
          {profile === undefined && !profileError && <p role="status">Cargando ficha…</p>}
          {profile && <p>{profile.job_title ? `${profile.job_title} · ` : ''}
            {profile.state === 'active' ? 'Ficha activa' : profile.state === 'pending' ? 'Ficha pendiente' : 'Ficha inactiva'}</p>}
          {(profile === null || profile?.state === 'pending') && (
            <form className="grid gap-2 rounded-xl border border-line p-3" onSubmit={accept}>
              <Field label="Código de invitación" htmlFor="staff-invitation">
                <input id="staff-invitation" type="password" autoComplete="off" required minLength={32} maxLength={128}
                  className={inputCls} value={token} readOnly={busy} onChange={event => setToken(event.target.value)} />
              </Field>
              <Button className="justify-self-start" type="submit" disabled={busy}>Aceptar invitación</Button>
            </form>
          )}
        </section>
        {profile?.state === 'active' && (
          <form className="grid gap-3 rounded-xl border border-line p-3" onSubmit={requestAccess}>
            <h3 className="font-semibold">Solicitar acceso</h3>
            <fieldset disabled={busy} className="grid min-w-0 gap-3">
              <Field label="Rol solicitado" htmlFor="staff-role">
                <select id="staff-role" className={inputCls} value={role} onChange={event => setRole(event.target.value as typeof role)}>
                  {Object.entries(roles).map(([id, label]) => <option key={id} value={id}>{label}</option>)}
                </select>
              </Field>
              <Field label="Ámbito" htmlFor="staff-scope">
                <select id="staff-scope" className={inputCls} value={scope} onChange={event => {
                  setScope(event.target.value as typeof scope)
                  setScopeId('')
                }}>
                  {Object.entries(scopes).map(([id, label]) => <option key={id} value={id}>{label}</option>)}
                </select>
              </Field>
              {scope !== 'global' && <Field label="Identificador del ámbito" htmlFor="staff-scope-id">
                <input id="staff-scope-id" className={inputCls} required maxLength={30} value={scopeId} onChange={event => setScopeId(event.target.value)} />
              </Field>}
              <Button type="submit" className="justify-self-start">Enviar solicitud de acceso</Button>
            </fieldset>
          </form>
        )}
        {(canReview || profile?.state === 'active') && (
          <section className="grid gap-3" aria-label={canReview ? 'Cola de aprobaciones' : 'Mis solicitudes de acceso'}>
            <h3 className="font-semibold">{canReview ? 'Cola de aprobaciones' : 'Mis solicitudes de acceso'}</h3>
            {canReview && <>
              <p className="text-sm text-muted">Aprobar una solicitud deja constancia de la revisión. El permiso se aplica en un paso administrativo separado.</p>
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={pendingOnly} disabled={busy} onChange={event => {
                  setOffset(0)
                  setPendingOnly(event.target.checked)
                }} />
                Solo pendientes de revisión
              </label>
            </>}
            {queueError && <Notice tone="warning" live="assertive">{queueError}</Notice>}
            {!queue && !queueError && <p role="status">Cargando solicitudes…</p>}
            {queue && <>
              {!queue.items.length && <p>No hay solicitudes en esta página.</p>}
              <ul className="grid gap-2">
                {queue.items.map(item => (
                  <li key={item.id} className="grid gap-2 rounded-xl border border-line p-3">
                    <p className="font-medium">{roles[item.requested_role as keyof typeof roles] ?? item.requested_role}
                      {' · '}{scopes[item.scope_type as keyof typeof scopes] ?? item.scope_type}{item.scope_id && ` · ${item.scope_id}`}</p>
                    <p className="text-sm">{states[item.state] ?? item.state} · {dateTime.format(new Date(item.requested_at))}</p>
                    {canReview && <p className="break-all text-xs text-muted">
                      {item.requested_by_name ?? `Ficha: ${item.staff_profile_id}`}
                    </p>}
                    {canReview && item.state === 'requested' && item.requested_by === me.id &&
                      <p className="text-sm">Esta solicitud requiere la revisión de otra persona administradora.</p>}
                    {canReview && item.state === 'requested' && item.requested_by !== me.id && (
                      <div className="flex flex-wrap gap-2">
                        <Button size="sm" disabled={busy} onClick={() => review(item, true)}>Aprobar solicitud</Button>
                        <Button size="sm" variant="ghost" disabled={busy} onClick={() => review(item, false)}>Rechazar solicitud</Button>
                      </div>
                    )}
                  </li>
                ))}
              </ul>
              {(offset > 0 || offset + PAGE_SIZE < queue.total) && (
                <nav aria-label="Páginas de solicitudes" className="flex gap-2">
                  <Button size="sm" variant="ghost" disabled={busy || offset === 0} onClick={() => setOffset(offset - PAGE_SIZE)}>Anterior</Button>
                  <Button size="sm" variant="ghost" disabled={busy || offset + PAGE_SIZE >= queue.total} onClick={() => setOffset(offset + PAGE_SIZE)}>Siguiente</Button>
                </nav>
              )}
            </>}
          </section>
        )}
      </div>
    </Modal>
  )
}
