import { useEffect, useRef, useState } from 'react'
import { api, errorMessage, type Schemas } from '../../../shared/api/client'
import { Button, Card, Field, Notice, inputCls } from '../../ui'

export function AcademicEmail({ cohortId }: { cohortId: string }) {
  const [recipients, setRecipients] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [recipient, setRecipient] = useState('')
  const [topic, setTopic] = useState('')
  const [scheduled, setScheduled] = useState(false)
  const [sendAt, setSendAt] = useState('')
  const [draft, setDraft] = useState<{ enrollment_id: string; topic: string; available_at: string; idempotency_key: string } | null>(null)
  const [busy, setBusy] = useState(false)
  const [uncertain, setUncertain] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const lock = useRef(false)
  const [history, setHistory] = useState<Schemas['NotificationHistoryOut'][]>([])
  const [historyError, setHistoryError] = useState('')
  const [historyLoading, setHistoryLoading] = useState(true)
  const [revision, setRevision] = useState(0)
  useEffect(() => {
    const controller = new AbortController()
    setHistoryLoading(true)
    setHistoryError('')
    void api.GET('/api/v1/cohorts/{cohort_id}/email/notifications', {
      params: { path: { cohort_id: cohortId } }, signal: controller.signal,
    }).then(result => {
      if (controller.signal.aborted) return
      if (result.data) setHistory(result.data)
      else { setHistory([]); setHistoryError(errorMessage(result.error)) }
    }).catch(() => {
      if (!controller.signal.aborted) { setHistory([]); setHistoryError('No se pudo consultar el historial.') }
    }).finally(() => {
      if (!controller.signal.aborted) setHistoryLoading(false)
    })
    return () => controller.abort()
  }, [cohortId, revision])
  useEffect(() => {
    const controller = new AbortController()
    void api.GET('/api/v1/cohorts/{cohort_id}/attendance-summary', {
      params: { path: { cohort_id: cohortId } }, signal: controller.signal,
    }).then(result => {
      if (controller.signal.aborted) return
      if (result.data) setRecipients(result.data.items.map(item => item.enrollment_id))
      else setError(errorMessage(result.error))
    }).catch(() => {
      if (!controller.signal.aborted) setError('No se pudieron consultar las matrículas.')
    }).finally(() => {
      if (!controller.signal.aborted) setLoading(false)
    })
    return () => controller.abort()
  }, [cohortId])
  const valid = (!scheduled || (Number.isFinite(Date.parse(sendAt)) && Date.parse(sendAt) > Date.now())) && recipients.includes(recipient) && topic.trim().length > 0 && topic.trim().length <= 120 && !Array.from(topic).some(c => c.charCodeAt(0) < 32)
  async function submit() {
    if (!draft || lock.current) return
    lock.current = true
    setBusy(true)
    setError('')
    try {
      const result = await api.POST('/api/v1/cohorts/{cohort_id}/email/notifications', {
        params: { path: { cohort_id: cohortId } }, body: draft,
      })
      if (result.data) {
        setMessage('Solicitud aceptada en la cola. No confirma la entrega. Referencia: ' + result.data.message_id)
        setRevision(n => n + 1)
        setDraft(null)
        setUncertain(false)
        setTopic('')
        setRecipient('')
        setScheduled(false)
        setSendAt('')
      } else {
        if (result.response.status >= 500 || result.response.status === 409 || result.response.status === 408) setUncertain(true)
        setError(errorMessage(result.error))
      }
    } catch {
      setUncertain(true)
      setError('No se pudo confirmar la solicitud. Reintenta con la misma referencia para evitar duplicados.')
    } finally {
      lock.current = false
      setBusy(false)
    }
  }
  return <Card title="Notificación académica">
    <p className="text-sm text-muted">Solo matrículas del ámbito autorizado. El servidor verifica que estén activas y que tengas permiso de envío. No introduzcas datos sensibles.</p>
    {loading && <Notice live="polite">Cargando matrículas…</Notice>}
    {error && <Notice tone="warning" live="assertive">{error}</Notice>}
    {message && <Notice live="polite">{message}</Notice>}
    {!loading && !recipients.length && <Notice>No hay matrículas disponibles para seleccionar.</Notice>}
    <Field label="Matrícula destinataria" htmlFor="email-recipient">
      <select id="email-recipient" className={inputCls} value={recipient} disabled={busy || !!draft} onChange={e => { setRecipient(e.target.value); setMessage('') }}>
        <option value="">Selecciona una matrícula</option>
        {recipients.map(id => <option key={id} value={id}>{id}</option>)}
      </select>
    </Field>
    <Field label="Tema del aviso" htmlFor="email-topic">
      <input id="email-topic" className={inputCls} maxLength={120} value={topic} disabled={busy || !!draft} onChange={e => { setTopic(e.target.value); setMessage('') }} />
    </Field>
    <label className="flex items-center gap-2 text-sm">
      <input type="checkbox" checked={scheduled} disabled={busy || !!draft} onChange={e => setScheduled(e.target.checked)} /> Programar envío
    </label>
    {scheduled && <Field label="Fecha y hora de envío (hora local)" htmlFor="email-send-at">
      <input id="email-send-at" type="datetime-local" className={inputCls} value={sendAt} disabled={busy || !!draft} onChange={e => setSendAt(e.target.value)} />
    </Field>}
    {!draft ? <Button disabled={!valid || busy} onClick={() => {
      if (!valid || (scheduled && Date.parse(sendAt) <= Date.now())) return
      setError('')
      setDraft({ enrollment_id: recipient, topic: topic.trim(), available_at: scheduled ? new Date(sendAt).toISOString() : new Date().toISOString(), idempotency_key: crypto.randomUUID() })
    }}>Revisar aviso</Button> : <>
      <div className="grid gap-2 text-sm">
        <p><b>Asunto:</b> Aviso académico: {draft.topic}</p>
        <p>Hay una actualización relacionada con {draft.topic}.</p>
        <p>Consulta EduGest para conocer los detalles.</p>
        <p>Destinatario: {draft.enrollment_id}</p>
        <p>Disponible para envío: {new Date(draft.available_at).toLocaleString('es-ES', { timeZoneName: 'short' })}</p>
      </div>
      {uncertain && <Notice tone="warning">Resultado no confirmado. Conserva esta referencia y consulta el historial. Si reintentas, se utilizará la misma clave para evitar duplicados.</Notice>}
      <Button disabled={busy} onClick={() => void submit()}>{uncertain ? 'Reintentar con la misma referencia' : 'Confirmar solicitud de envío'}</Button>
      <Button variant="ghost" disabled={busy || uncertain} onClick={() => { setDraft(null); setError('') }}>Descartar revisión</Button>
    </>}
    <section className="mt-6 grid gap-3">
      <h3 className="font-semibold">Mis comunicaciones recientes</h3>
      <Button variant="ghost" disabled={historyLoading} onClick={() => setRevision(n => n + 1)}>Actualizar historial</Button>
      {historyLoading && <Notice live="polite">Consultando historial…</Notice>}
      {historyError && <Notice tone="warning">{historyError}</Notice>}
      {!historyLoading && !historyError && !history.length && <Notice>No hay solicitudes registradas.</Notice>}
      {!historyLoading && !historyError && history.map(item => <div key={item.message_id} className="grid gap-1 text-sm">
        <b>{{ pending: 'Pendiente', sending: 'En proceso', sent: 'Aceptado por SMTP', failed: 'Fallido', uncertain: 'Resultado incierto', cancelled: 'Cancelado' }[item.status as 'pending'] ?? item.status}</b>
        <span>Intentos: {item.attempts} · {new Date(item.created_at).toLocaleString('es-ES')}</span>
        <span>Disponible desde: {new Date(item.available_at).toLocaleString('es-ES')}</span>
        {item.sent_at && <span>Aceptado por SMTP: {new Date(item.sent_at).toLocaleString('es-ES', { timeZoneName: 'short' })}</span>}
        {item.status === 'uncertain' && <p className="text-muted">Entrega no confirmada. No generes otra solicitud sin revisar el resultado.</p>}
        <span className="break-all text-xs">{item.message_id}</span>
      </div>)}
    </section>
  </Card>
}
