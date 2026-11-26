import { useEffect, useRef, useState, type FormEvent } from 'react'
import { api, type Schemas } from '../../../shared/api/client'
import { describeApiError, problemText } from '../../../shared/api/errors'
import type { Me } from '../../../shared/api/session'
import { Modal } from '../../components/Modal'
import { StaffInvitationConsole } from './StaffInvitationConsole'
import { Button, Field, Notice, inputCls } from '../../ui'

type Profile = Schemas['StaffProfileOut']
type AccessRequest = Schemas['AccessRequestOut']
type RequestInput = Schemas['AccessRequestCreate']
type Preview = Schemas['AccessApplicationPreview']
type Application = Schemas['AccessApplicationOut']
type QueueFilter = 'requested' | 'approved' | 'all'
type Result<T> = { data?: T; error?: unknown; response: Response }

const PAGE_SIZE = 20
const roles = { admin: 'Administración', captacion: 'Captación', seleccion: 'Selección', docente: 'Docencia', coordinacion: 'Coordinación' }
const scopes = { global: 'Global', program: 'Programa', call: 'Convocatoria', cohort: 'Cohorte' }
const states: Record<string, string> = {
  requested: 'Pendiente de revisión', approved: 'Aprobada, pendiente de aplicación', rejected: 'Rechazada',
  applied: 'Aplicada', revoked: 'Revocada',
}
const blockers: Record<string, string> = {
  request_not_approved: 'La solicitud ya no está pendiente de aplicación.',
  staff_account_required: 'La cuenta interna debe estar activa.',
  active_staff_profile_required: 'La ficha interna debe estar activa.',
  invalid_request_owner: 'La solicitud no coincide con la persona titular de la ficha.',
  invalid_review: 'Falta una revisión válida de otra persona administradora.',
  self_application: 'Otra persona administradora debe aplicar esta solicitud.',
  scope_not_found: 'El ámbito solicitado ya no existe.',
  active_assignment_exists: 'Ya hay una asignación activa con ese rol y ámbito.',
}
const dateTime = new Intl.DateTimeFormat('es-ES', { dateStyle: 'medium', timeStyle: 'short', timeZone: 'Europe/Madrid' })

function requestProblem(result: Result<unknown>) {
  return problemText(describeApiError(result.response.status, result.error))
}

export function StaffAccessPanel({ me, onClose }: { me: Me; onClose: () => void }) {
  const canReview = me.roles.some(role => role.role === 'admin' && role.scope_type === 'global')
  const [profile, setProfile] = useState<Profile | null>()
  const canList = canReview || profile?.state === 'active'
  const [profileError, setProfileError] = useState('')
  const [queue, setQueue] = useState<Schemas['AccessRequestList']>()
  const [queueError, setQueueError] = useState('')
  const [offset, setOffset] = useState(0)
  const [filter, setFilter] = useState<QueueFilter>('requested')
  const [inspection, setInspection] = useState<AccessRequest | null>(null)
  const [details, setDetails] = useState<{ preview: Preview } | { application: Application }>()
  const [inspectionError, setInspectionError] = useState('')
  const [attempt, setAttempt] = useState(0)
  const [token, setToken] = useState('')
  const [role, setRole] = useState<RequestInput['requested_role']>('docente')
  const [scope, setScope] = useState<RequestInput['scope_type']>('cohort')
  const [scopeId, setScopeId] = useState('')
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [uncertain, setUncertain] = useState(false)
  const pending = useRef<AbortController | null>(null)

  useEffect(() => () => pending.current?.abort(), [])
  useEffect(() => {
    const controller = new AbortController()
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
    if (!canList) return
    const controller = new AbortController()
    void api.GET('/api/v1/staff/access-requests', {
      params: { query: { limit: PAGE_SIZE, offset, state: canReview && filter !== 'all' ? filter : undefined } }, signal: controller.signal,
    }).then(result => {
      if (controller.signal.aborted) return
      if (result.data) {
        if (offset > 0 && offset >= result.data.total) setOffset(Math.max(0, Math.floor((result.data.total - 1) / PAGE_SIZE) * PAGE_SIZE))
        else setQueue(result.data)
      }
      else setQueueError(requestProblem(result))
    }).catch(() => {
      if (!controller.signal.aborted) setQueueError('No se pudo cargar la cola de solicitudes.')
    })
    return () => controller.abort()
  }, [canReview, canList, offset, attempt, filter])

  useEffect(() => {
    setDetails(undefined)
    setInspectionError('')
    if (!inspection || !canList) return
    const controller = new AbortController()
    const params = { path: { request_id: inspection.id } }
    void (async () => {
      try {
        if (canReview && inspection.state === 'approved') {
          const result = await api.GET('/api/v1/staff/access-requests/{request_id}/application-preview', { params, signal: controller.signal })
          if (controller.signal.aborted) return
          if (result.data) setDetails({ preview: result.data })
          else setInspectionError(requestProblem(result))
        } else {
          const result = await api.GET('/api/v1/staff/access-requests/{request_id}/application', { params, signal: controller.signal })
          if (controller.signal.aborted) return
          if (result.data) setDetails({ application: result.data })
          else setInspectionError(requestProblem(result))
        }
      } catch {
        if (!controller.signal.aborted) setInspectionError('No se pudo consultar la aplicación del acceso.')
      }
    })()
    return () => controller.abort()
  }, [inspection, canReview, canList, attempt])

  async function write(send: (signal: AbortSignal) => Promise<Result<unknown>>, onSuccess: () => void) {
    if (pending.current || uncertain) return
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
      } else {
        setError(requestProblem(result))
        if (result.response.status >= 500 || result.response.status === 408) setUncertain(true)
        if (result.response.status === 409) {
          setInspection(null)
          setQueue(undefined)
          setAttempt(value => value + 1)
        }
      }
    } catch {
      if (!controller.signal.aborted) {
        setUncertain(true)
        setError('No se pudo confirmar el cambio. Cierra y vuelve a abrir el panel para comprobar el estado antes de repetirlo.')
      }
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
      setOffset(0)
      setNotice('Solicitud registrada y pendiente de revisión.')
    })
  }

  function review(request: AccessRequest, approved: boolean) {
    if (!canReview || request.requested_by === me.id || request.state !== 'requested') return
    const requester = `${request.requested_by_name ?? 'Sin nombre'} · Ficha: ${request.staff_profile_id}`
    const requestedRole = roles[request.requested_role as keyof typeof roles] ?? request.requested_role
    const requestedScope = scopes[request.scope_type as keyof typeof scopes] ?? request.scope_type
    if (!window.confirm(`${approved ? '¿Aprobar' : '¿Rechazar'} la solicitud?\n${requester}\nRol: ${requestedRole}\nÁmbito: ${requestedScope}${request.scope_id ? ` · ${request.scope_id}` : ''}`)) return
    void write(signal => api.POST('/api/v1/staff/access-requests/{request_id}/review', {
      params: { path: { request_id: request.id } }, body: { approved }, signal,
    }), () => setNotice(approved ? 'Solicitud aprobada. La aplicación del permiso sigue pendiente.' : 'Solicitud rechazada.'))
  }

  function apply(preview: Preview) {
    if (!canReview || !preview.can_apply || preview.request_id !== inspection?.id || inspection.requested_by === me.id) return
    void write(signal => api.POST('/api/v1/staff/access-requests/{request_id}/apply', {
      params: { path: { request_id: preview.request_id } },
      body: { ...preview.requested, confirm: true },
      signal,
    }), () => {
      setInspection(null)
      setNotice('Aplicación del permiso registrada. Consulta el estado en Todas las solicitudes.')
    })
  }

  function revoke(item: AccessRequest, application: Application) {
    if (!canReview || item.requested_by === me.id || item.state !== 'applied' ||
      application.request_id !== item.id || application.request_state !== 'applied' ||
      !application.assignment_active || !application.assignment_id) return
    if (!window.confirm(`¿Revocar el permiso de ${item.requested_by_name ?? 'esta cuenta'}?\nRol: ${item.requested_role}\nÁmbito: ${item.scope_type} ${item.scope_id ?? ''}\nSe conservará el historial.`)) return
    void write(signal => api.POST('/api/v1/staff/access-requests/{request_id}/revoke-access', {
      params: { path: { request_id: item.id } },
      body: { requested_role: item.requested_role as RequestInput['requested_role'], scope_type: item.scope_type as RequestInput['scope_type'], scope_id: item.scope_id, assignment_id: application.assignment_id!, confirm: true }, signal,
    }), () => {
      setInspection(null)
      setNotice('Revocación registrada. El historial de la asignación se conserva.')
    })
  }

  return (
    <Modal open onClose={() => { if (!pending.current) onClose() }} placement="end" size="md" title="Personal y accesos"
      dirty={!busy && Boolean(token || scopeId)}
      subtitle="Ficha interna y solicitudes de cambio de acceso.">
      <div className="grid gap-5">
        {notice && <Notice live="polite">{notice}</Notice>}
        {error && <Notice live="assertive" tone="warning">{error}</Notice>}
        {uncertain && <Notice tone="warning">Operaciones bloqueadas por un resultado incierto. Cierra y vuelve a abrir el panel para comprobar el estado antes de repetir la operación.</Notice>}
        <section className="grid gap-3" aria-label="Ficha interna">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h3 className="font-semibold">Mi ficha interna</h3>
            <Button size="sm" variant="ghost" disabled={busy} onClick={() => { setError(''); setAttempt(value => value + 1) }}>Actualizar personal</Button>
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
              <Button className="justify-self-start" type="submit" disabled={busy || uncertain}>Aceptar invitación</Button>
            </form>
          )}
        </section>
        {canReview && <StaffInvitationConsole />}
        {profile?.state === 'active' && (
          <form className="grid gap-3 rounded-xl border border-line p-3" onSubmit={requestAccess}>
            <h3 className="font-semibold">Solicitar acceso</h3>
            <fieldset disabled={busy || uncertain} className="grid min-w-0 gap-3">
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
              <Field label="Estado de solicitudes" htmlFor="staff-queue-state">
                <select id="staff-queue-state" className={inputCls} value={filter} disabled={busy || uncertain} onChange={event => {
                  setInspection(null)
                  setOffset(0)
                  setFilter(event.target.value as QueueFilter)
                }}>
                  <option value="requested">Pendientes de revisión</option>
                  <option value="approved">Aprobadas pendientes de aplicación</option>
                  <option value="all">Todas las solicitudes</option>
                </select>
              </Field>
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
                      {item.requested_by_name ?? 'Sin nombre'} · Ficha: {item.staff_profile_id}
                    </p>}
                    {canReview && item.state === 'requested' && item.requested_by === me.id &&
                      <p className="text-sm">Esta solicitud requiere la revisión de otra persona administradora.</p>}
                    {canReview && item.state === 'requested' && item.requested_by !== me.id && (
                      <div className="flex flex-wrap gap-2">
                        <Button size="sm" disabled={busy || uncertain} onClick={() => review(item, true)}>Aprobar solicitud</Button>
                        <Button size="sm" variant="ghost" disabled={busy || uncertain} onClick={() => review(item, false)}>Rechazar solicitud</Button>
                      </div>
                    )}
                    {item.state !== 'requested' && <Button size="sm" variant="ghost" className="justify-self-start"
                      aria-expanded={inspection?.id === item.id} disabled={busy || uncertain}
                      onClick={() => {
                        setDetails(undefined)
                        setInspectionError('')
                        setInspection(inspection?.id === item.id ? null : item)
                      }}>
                      {inspection?.id === item.id ? 'Ocultar detalles' : canReview && item.state === 'approved' ? 'Previsualizar aplicación' : 'Consultar aplicación'}
                    </Button>}
                    {inspection?.id === item.id && (
                      <div className="grid gap-2 rounded-lg bg-mist p-3 text-sm">
                        {inspectionError && <Notice tone="warning" live="assertive">{inspectionError}</Notice>}
                        {!inspectionError && !details && <p role="status">Consultando aplicación…</p>}
                        {details && 'application' in details && <>
                          <p>{states[details.application.request_state] ?? details.application.request_state}</p>
                          {details.application.assignment_active !== null && <p>
                            {details.application.assignment_active ? 'Asignación registrada sin revocación.' : 'La asignación está revocada.'}
                          </p>}
                          {canReview && item.requested_by !== me.id && item.state === 'applied' && details.application.request_state === 'applied' && details.application.assignment_active && details.application.assignment_id &&
                            <Button size="sm" variant="ghost" disabled={busy || uncertain} onClick={() => revoke(item, details.application)}>Revocar permiso</Button>}
                          {details.application.request_state === 'applied' && details.application.assignment_active === null &&
                            <p>No se pudo verificar la asignación vinculada.</p>}
                        </>}
                        {details && 'preview' in details && <>
                          <p className="font-medium">Aplicación para {item.requested_by_name ?? 'Cuenta interna'}</p>
                          <p>{roles[details.preview.requested.requested_role]} · {scopes[details.preview.requested.scope_type]}
                            {details.preview.requested.scope_id && ` · ${details.preview.requested.scope_id}`}</p>
                          {details.preview.can_apply ? <Button size="sm" className="justify-self-start" disabled={busy || uncertain}
                            onClick={() => apply(details.preview)}>Confirmar y aplicar permiso</Button> :
                            <ul className="list-disc pl-4">{details.preview.blockers.map(code =>
                              <li key={code}>{blockers[code] ?? 'La revisión del servidor impide aplicar esta solicitud.'}</li>)}</ul>}
                        </>}
                      </div>
                    )}
                  </li>
                ))}
              </ul>
              {(offset > 0 || offset + PAGE_SIZE < queue.total) && (
                <nav aria-label="Páginas de solicitudes" className="flex gap-2">
                  <Button size="sm" variant="ghost" disabled={busy || offset === 0} onClick={() => { setInspection(null); setOffset(offset - PAGE_SIZE) }}>Anterior</Button>
                  <Button size="sm" variant="ghost" disabled={busy || offset + PAGE_SIZE >= queue.total} onClick={() => { setInspection(null); setOffset(offset + PAGE_SIZE) }}>Siguiente</Button>
                </nav>
              )}
            </>}
          </section>
        )}
      </div>
    </Modal>
  )
}
