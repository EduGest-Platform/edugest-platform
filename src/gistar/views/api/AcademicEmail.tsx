import { useEffect, useRef, useState } from 'react'
import { api, errorMessage } from '../../../shared/api/client'
import { Button, Card, Field, Notice, inputCls } from '../../ui'

export function AcademicEmail({ cohortId }: { cohortId: string }) {
  const [recipients, setRecipients] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [recipient, setRecipient] = useState('')
  const [topic, setTopic] = useState('')
  const [draft, setDraft] = useState<{ enrollment_id: string; topic: string; available_at: string; idempotency_key: string } | null>(null)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const lock = useRef(false)
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
  const valid = recipients.includes(recipient) && topic.trim().length > 0 && topic.trim().length <= 120 && !Array.from(topic).some(c => c.charCodeAt(0) < 32)
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
        setDraft(null)
        setTopic('')
        setRecipient('')
      } else setError(errorMessage(result.error))
    } catch {
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
    {!draft ? <Button disabled={!valid || busy} onClick={() => {
      setError('')
      setDraft({ enrollment_id: recipient, topic: topic.trim(), available_at: new Date().toISOString(), idempotency_key: crypto.randomUUID() })
    }}>Revisar aviso</Button> : <>
      <div className="grid gap-2 text-sm">
        <p><b>Asunto:</b> Aviso académico: {draft.topic}</p>
        <p>Hay una actualización relacionada con {draft.topic}.</p>
        <p>Consulta EduGest para conocer los detalles.</p>
        <p>Destinatario: {draft.enrollment_id}</p>
      </div>
      <Button disabled={busy} onClick={() => void submit()}>Confirmar solicitud de envío</Button>
      <Button variant="ghost" disabled={busy} onClick={() => { setDraft(null); setError('') }}>Descartar revisión</Button>
    </>}
  </Card>
}
