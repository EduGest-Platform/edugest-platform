import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { CircleCheck, RefreshCw, Search, Send } from 'lucide-react'
import { api, type Schemas } from '../../../shared/api/client'
import { describeApiError, problemText } from '../../../shared/api/errors'
import { useApiSession } from '../../../shared/api/session'
import { humanize } from '../../config'
import { useGistar } from '../../store'
import { AccessDenied } from '../../components/AccessDenied'
import { Modal } from '../../components/Modal'
import { ServerRequirementReview } from './ServerRequirementReview'
import { Button, Card, Empty, Field, Notice, PageTitle, Status, Table, inputCls } from '../../ui'

type Call = Schemas['CallOut']
type Stage = Schemas['ApplicationSummary']['stage']
const STAGES: Stage[] = ['enviada', 'requisitos_en_revision', 'convocada', 'evaluacion_en_curso', 'pendiente_decision_humana', 'admitida', 'lista_espera', 'no_admitida', 'retirada']
const fmt = (iso: string) => new Intl.DateTimeFormat('es-ES', { dateStyle: 'medium', timeStyle: 'short', timeZone: 'Europe/Madrid' }).format(new Date(iso))

export function ServerBadge() {
  return <span className="rounded-md bg-teal-50 px-2 py-0.5 text-[11px] font-bold tracking-wide text-teal-800 ring-1 ring-inset ring-teal-600/20">Datos del servidor</span>
}

function useCalls(estado?: 'abierta') {
  const [calls, setCalls] = useState<Call[]>([])
  useEffect(() => {
    api.GET('/api/v1/calls', { params: { query: estado ? { estado } : {} } }).then(({ data }) => setCalls(data ?? []))
  }, [estado])
  return calls
}

/** Public inscription form (also used by a logged-in aspirant). Creates or reuses the Person record. */
export function InscriptionForm({ onDone }: { onDone?: (codigo: string) => void }) {
  const { me, refresh } = useApiSession()
  const calls = useCalls('abierta')
  const empty = () => ({ call_id: '', nombre: me?.display_name ?? '', email: me?.email ?? '', motivacion: '', disponibilidad: 'Mañana' as 'Mañana' | 'Tarde' | 'Flexible', acepta: false })
  const [f, setF] = useState(empty)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [receipt, setReceipt] = useState<Schemas['ApplicationReceipt'] | null>(null)
  const callId = f.call_id || calls[0]?.id || ''

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setBusy(true)
    setError(null)
    const { data, error: err, response } = await api.POST('/api/v1/applications', {
      body: { call_id: callId, nombre: f.nombre, email: f.email, motivacion: f.motivacion, disponibilidad: f.disponibilidad, acepta_datos_sinteticos: true },
    })
    setBusy(false)
    if (err || !data) return setError(problemText(describeApiError(response.status, err)))
    setReceipt(data)
    await refresh()
    onDone?.(data.codigo)
  }

  if (receipt)
    return (
      <div className="grid gap-3">
        <Notice>
          <CircleCheck className="mr-1 inline size-4 align-[-3px] text-teal-700" aria-hidden />
          Candidatura recibida con el código <b className="font-mono">{receipt.codigo}</b>. Se ha registrado en tu expediente único y en el historial.
        </Notice>
        <div>
          <Button
            variant="ghost"
            onClick={() => {
              setReceipt(null)
              setF({ ...empty(), call_id: f.call_id })
            }}
          >
            Enviar otra candidatura
          </Button>
        </div>
      </div>
    )

  return (
    <form onSubmit={submit} className="grid gap-4">
      <Field label="Convocatoria" htmlFor="ins-call">
        <select id="ins-call" className={inputCls} value={callId} onChange={(e) => setF({ ...f, call_id: e.target.value })} required>
          {calls.map((c) => (
            <option key={c.id} value={c.id}>
              {c.nombre} · {c.plazas} plazas
            </option>
          ))}
        </select>
      </Field>
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Nombre (ficticio)" htmlFor="ins-name">
          <input id="ins-name" className={inputCls} required minLength={2} maxLength={120} value={f.nombre} onChange={(e) => setF({ ...f, nombre: e.target.value })} />
        </Field>
        <Field label="Correo de demostración" htmlFor="ins-email" hint="Usa un dominio reservado, p. ej. @example.test">
          <input id="ins-email" type="email" className={inputCls} required value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} />
        </Field>
      </div>
      <Field label="Motivación" htmlFor="ins-mot">
        <textarea id="ins-mot" className={`${inputCls} min-h-24`} required minLength={10} maxLength={2000} value={f.motivacion} onChange={(e) => setF({ ...f, motivacion: e.target.value })} />
      </Field>
      <Field label="Disponibilidad" htmlFor="ins-av">
        <select id="ins-av" className={inputCls} value={f.disponibilidad} onChange={(e) => setF({ ...f, disponibilidad: e.target.value as typeof f.disponibilidad })}>
          <option>Mañana</option>
          <option>Tarde</option>
          <option>Flexible</option>
        </select>
      </Field>
      <label className="flex items-start gap-2.5 text-sm">
        <input type="checkbox" className="mt-0.5 size-4 accent-teal" required checked={f.acepta} onChange={(e) => setF({ ...f, acepta: e.target.checked })} />
        Entiendo que esta plataforma utiliza exclusivamente datos sintéticos
      </label>
      {error && (
        <Notice tone="warning" live="assertive">
          {error}
        </Notice>
      )}
      <div>
        <Button type="submit" disabled={busy || !callId}>
          <Send className="size-4" aria-hidden /> {busy ? 'Enviando…' : 'Enviar candidatura'}
        </Button>
      </div>
    </form>
  )
}

export function ApiInscription() {
  const { navigate } = useGistar()
  return (
    <>
      <PageTitle title="Inscripción" sub="Formulario único de solicitud. Se crea o reutiliza tu ficha de persona: nunca se duplica el expediente." />
      <Card title="Solicitud de acceso" action={<ServerBadge />} className="max-w-2xl">
        <InscriptionForm onDone={() => setTimeout(() => navigate('candidatura'), 1500)} />
      </Card>
    </>
  )
}

export function ApiMyApplications() {
  const { navigate } = useGistar()
  type Result =
    | { status: 'loading' }
    | { status: 'error'; message: string }
    | { status: 'ready'; items: Schemas['ApplicationSelfView'][] }
  const [result, setResult] = useState<Result>({ status: 'loading' })
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    const controller = new AbortController()

    async function loadApplications() {
      try {
        const { data, error, response } = await api.GET('/api/v1/me/applications', { signal: controller.signal })
        if (controller.signal.aborted) return
        setResult(data
          ? { status: 'ready', items: data }
          : { status: 'error', message: problemText(describeApiError(response.status, error)) })
      } catch {
        if (!controller.signal.aborted) {
          setResult({ status: 'error', message: 'No se pudo conectar con el servidor.' })
        }
      }
    }

    void loadApplications()
    return () => controller.abort()
  }, [attempt])
  return (
    <>
      <PageTitle title="Mi candidatura" sub="Estado de tus solicitudes. La evaluación y la admisión siempre las deciden personas autorizadas." />
      <Card title="Mis solicitudes" action={<ServerBadge />}>
        {result.status === 'loading' ? (
          <p role="status" className="text-sm text-muted">Cargando…</p>
        ) : result.status === 'error' ? (
          <div className="grid justify-items-start gap-3">
            <Notice tone="warning" live="assertive">{result.message}</Notice>
            <Button type="button" variant="ghost" onClick={() => {
              setResult({ status: 'loading' })
              setAttempt((previous) => previous + 1)
            }}>
              Volver a intentar
            </Button>
          </div>
        ) : !result.items.length ? (
          <Empty>
            Aún no has enviado ninguna candidatura.{' '}
            <button type="button" className="cursor-pointer font-semibold text-blue underline" onClick={() => navigate('inscripcion')}>
              Ir a Inscripción
            </button>
          </Empty>
        ) : (
          <ul className="grid gap-3">
            {result.items.map((a) => (
              <li key={a.id} className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-line px-4 py-3">
                <div>
                  <p className="font-medium">{a.call_nombre}</p>
                  <p className="text-xs text-muted">
                    <span className="font-mono">{a.codigo}</span> · enviada {fmt(a.created_at)} · actualizada {fmt(a.updated_at)}
                  </p>
                </div>
                <Status s={a.stage} />
              </li>
            ))}
          </ul>
        )}
        <Notice>No se muestran notas internas del equipo: solo el estado de tu solicitud.</Notice>
      </Card>
    </>
  )
}

export function ApiApplications() {
  const calls = useCalls()
  const [callId, setCallId] = useState('')
  const [stage, setStage] = useState<Stage | ''>('')
  const [q, setQ] = useState('')
  const [res, setRes] = useState<{ items: Schemas['ApplicationSummary'][]; total: number } | null>(null)
  const [denied, setDenied] = useState(false)
  const [open, setOpen] = useState<string | null>(null)

  const load = useCallback(async () => {
    const { data, response } = await api.GET('/api/v1/applications', {
      params: { query: { call_id: callId || undefined, stage: stage || undefined, q: q.trim() || undefined, limit: 200 } },
    })
    if (response.status === 403) return setDenied(true)
    setDenied(false)
    setRes(data ?? null)
  }, [callId, stage, q])

  useEffect(() => {
    const t = setTimeout(load, 250)
    return () => clearTimeout(t)
  }, [load])
  useEffect(() => {
    window.addEventListener('focus', load)
    return () => window.removeEventListener('focus', load)
  }, [load])

  if (denied)
    return (
      <>
        <PageTitle title="Candidaturas" sub="Expedientes de preselección y selección." />
        <AccessDenied reason="Los expedientes de admisión solo están disponibles para algunos perfiles." />
      </>
    )

  return (
    <>
      <PageTitle title="Candidaturas" sub="Expedientes únicos con historial CRM. Solo ves las convocatorias de tu ámbito: lo filtra la API." />
      <Card
        title="Expedientes"
        action={
          <div className="flex items-center gap-2">
            <span role="status" className="text-xs text-muted">{res ? `${res.total} en tu ámbito` : 'Cargando…'}</span>
            <Button size="sm" variant="ghost" onClick={load} aria-label="Actualizar">
              <RefreshCw className="size-3.5" aria-hidden />
            </Button>
            <ServerBadge />
          </div>
        }
      >
        <div className="mb-4 flex flex-wrap items-end gap-3">
          <div className="min-w-56 flex-1">
            <Field label="Buscar expedientes" htmlFor="application-search">
              <div className="relative">
                <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-slate-400" aria-hidden />
                <input id="application-search" aria-label="Buscar expedientes" placeholder="Nombre, correo o código" value={q} onChange={(e) => setQ(e.target.value)} className={`${inputCls} pl-9`} />
              </div>
            </Field>
          </div>
          <Field label="Convocatoria" htmlFor="application-call">
            <select id="application-call" className={`${inputCls} w-auto`} value={callId} onChange={(e) => setCallId(e.target.value)}>
              <option value="">Todas las convocatorias</option>
              {calls.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.nombre}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Etapa" htmlFor="application-stage">
            <select id="application-stage" className={`${inputCls} w-auto`} value={stage} onChange={(e) => setStage(e.target.value as Stage | '')}>
              <option value="">Todas las etapas</option>
              {STAGES.map((s) => (
                <option key={s} value={s}>
                  {humanize(s)}
                </option>
              ))}
            </select>
          </Field>
        </div>
        {res && !res.items.length ? (
          <Empty>No hay expedientes con estos filtros en tu ámbito.</Empty>
        ) : (
          <Table head={['Código', 'Persona', 'Convocatoria', 'Etapa', 'Recibida', '']}>
            {(res?.items ?? []).map((a) => (
              <tr key={a.id}>
                <td className="pl-2 font-mono text-xs">{a.codigo}</td>
                <td>
                  <p className="font-medium">{a.person.display_name}</p>
                  <p className="text-xs text-muted">{a.person.email}</p>
                </td>
                <td className="text-xs text-muted">{a.call_id}</td>
                <td>
                  <Status s={a.stage} />
                </td>
                <td className="whitespace-nowrap text-xs text-muted">{fmt(a.created_at)}</td>
                <td className="text-right">
                  <Button size="sm" variant="ghost" onClick={() => setOpen(a.id)}>
                    Abrir ficha
                  </Button>
                </td>
              </tr>
            ))}
          </Table>
        )}
      </Card>
      {open && <ApplicationFile id={open} onClose={() => setOpen(null)} onChanged={load} />}
    </>
  )
}

function ApplicationFile({ id, onClose, onChanged }: { id: string; onClose: () => void; onChanged: () => void }) {
  const { toast } = useGistar()
  const [d, setD] = useState<Schemas['ApplicationDetail'] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [ev, setEv] = useState<{ tipo: 'contacto' | 'nota' | 'recordatorio'; canal: '' | 'email' | 'telefono' | 'presencial' | 'videollamada'; resumen: string }>({ tipo: 'contacto', canal: 'telefono', resumen: '' })
  const [busy, setBusy] = useState(false)

  const load = useCallback(async () => {
    const { data, error: err, response } = await api.GET('/api/v1/applications/{application_id}', { params: { path: { application_id: id } } })
    if (err) setError(problemText(describeApiError(response.status, err)))
    setD(data ?? null)
  }, [id])
  useEffect(() => {
    load()
  }, [load])

  const add = async () => {
    setBusy(true)
    const { error: err, response } = await api.POST('/api/v1/applications/{application_id}/events', {
      params: { path: { application_id: id } },
      body: { tipo: ev.tipo, canal: ev.canal || null, resumen: ev.resumen },
    })
    setBusy(false)
    if (err) return toast(problemText(describeApiError(response.status, err)))
    setEv({ ...ev, resumen: '' })
    toast('Evento registrado en el historial')
    await load()
    onChanged()
  }

  return (
    <Modal
      open
      size="lg"
      onClose={onClose}
      dirty={!!ev.resumen.trim()}
      title={d ? `${d.person.display_name} · ${d.codigo}` : 'Expediente'}
      subtitle={d ? `${d.call_id} · ${d.person.email}` : undefined}
      footer={<Button onClick={onClose}>Cerrar</Button>}
    >
      {error && (
        <Notice tone="warning" live="assertive">
          {error}
        </Notice>
      )}
      {!d ? (
        !error && <p className="text-sm text-muted">Cargando…</p>
      ) : (
        <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)]">
          <section className="grid content-start gap-3 text-sm">
            <div className="flex items-center gap-2">
              <Status s={d.stage} />
              {d.legacy_ref && <span className="text-xs text-muted">Ref. dataset {d.legacy_ref}</span>}
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-muted">Motivación</p>
              <p className="mt-1 leading-relaxed">{d.motivacion}</p>
            </div>
            <p>
              <span className="text-muted">Disponibilidad:</span> {d.disponibilidad}
            </p>
            <ServerRequirementReview key={`${d.id}:${d.call_id}`} applicationId={d.id} callId={d.call_id} />
            <Notice>Los cambios de etapa, la valoración y la decisión se registrarán con revisión humana en el siguiente incremento (F2).</Notice>
          </section>
          <section>
            <h3 className="mb-3 text-sm font-semibold">Historial CRM</h3>
            <ol className="mb-4 grid gap-2">
              {d.events.map((e) => (
                <li key={e.id} className="rounded-lg border border-line px-3 py-2 text-sm">
                  <p className="text-xs text-muted">
                    {fmt(e.occurred_at)} · <b className="font-semibold text-ink/80">{humanize(e.tipo)}</b>
                    {e.canal && ` · ${e.canal}`} · {e.actor ?? 'Sistema / formulario'}
                  </p>
                  <p className="mt-0.5">{e.resumen}</p>
                </li>
              ))}
            </ol>
            <div className="grid gap-2 rounded-xl bg-mist/60 p-3">
              <div className="flex flex-wrap gap-2">
                <select aria-label="Tipo de evento" className={`${inputCls} w-auto py-1.5`} value={ev.tipo} onChange={(e) => setEv({ ...ev, tipo: e.target.value as typeof ev.tipo })}>
                  <option value="contacto">Contacto</option>
                  <option value="nota">Nota</option>
                  <option value="recordatorio">Recordatorio</option>
                </select>
                <select aria-label="Canal" className={`${inputCls} w-auto py-1.5`} value={ev.canal} onChange={(e) => setEv({ ...ev, canal: e.target.value as typeof ev.canal })}>
                  <option value="">Sin canal</option>
                  <option value="telefono">Teléfono</option>
                  <option value="email">Email</option>
                  <option value="presencial">Presencial</option>
                  <option value="videollamada">Videollamada</option>
                </select>
              </div>
              <textarea
                aria-label="Resumen del evento"
                maxLength={500}
                placeholder="Resumen operativo (sin datos de salud ni situación personal)"
                className={`${inputCls} min-h-16`}
                value={ev.resumen}
                onChange={(e) => setEv({ ...ev, resumen: e.target.value })}
              />
              <div>
                <Button size="sm" disabled={busy || !ev.resumen.trim()} onClick={add}>
                  Registrar en el historial
                </Button>
              </div>
            </div>
          </section>
        </div>
      )}
    </Modal>
  )
}

export function ApiAudit() {
  const [rows, setRows] = useState<Schemas['AuditEventOut'][] | null>(null)
  const [denied, setDenied] = useState(false)
  const load = useCallback(async () => {
    const { data, response } = await api.GET('/api/v1/audit-events', { params: { query: { limit: 200 } } })
    if (response.status === 403) return setDenied(true)
    setRows(data ?? [])
  }, [])
  useEffect(() => {
    load()
  }, [load])
  return (
    <>
      <PageTitle title="Auditoría del servidor" sub="Registro de solo inserción (lo impide un trigger de PostgreSQL). Contiene identificadores y acciones, nunca datos personales ni texto libre." />
      {denied ? (
        <AccessDenied reason="El registro de auditoría solo está disponible para algunos perfiles." />
      ) : (
        <Card
          title="Eventos recientes"
          action={
            <div className="flex items-center gap-2">
              <Button size="sm" variant="ghost" onClick={load} aria-label="Actualizar">
                <RefreshCw className="size-3.5" aria-hidden />
              </Button>
              <ServerBadge />
            </div>
          }
        >
          <Table head={['Fecha', 'Roles del actor', 'Acción', 'Objeto', 'Metadatos']}>
            {(rows ?? []).map((r) => (
              <tr key={r.id}>
                <td className="whitespace-nowrap text-xs tabular-nums text-muted">{fmt(r.at)}</td>
                <td className="text-xs">{r.actor_roles || (r.actor_user_id ? 'persona' : 'anónimo')}</td>
                <td className="font-mono text-xs">{r.action}</td>
                <td className="text-xs">
                  {r.target_type}
                  {r.target_id && <span className="ml-1 font-mono text-muted">{r.target_id.slice(0, 8)}</span>}
                </td>
                <td className="max-w-72 truncate font-mono text-[11px] text-muted">{JSON.stringify(r.meta)}</td>
              </tr>
            ))}
          </Table>
        </Card>
      )}
    </>
  )
}
