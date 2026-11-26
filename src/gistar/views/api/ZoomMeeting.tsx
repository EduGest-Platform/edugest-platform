import { useEffect, useRef, useState } from "react"
import { api, errorMessage, type Schemas } from "../../../shared/api/client"
import { Button, Field, Notice, inputCls } from "../../ui"

export function ZoomMeeting({ sessions }: { sessions: Schemas["SessionOut"][] }) {
  const [sessionId, setSessionId] = useState("")
  const [topic, setTopic] = useState("")
  const [start, setStart] = useState("")
  const [duration, setDuration] = useState("60")
  const [mode, setMode] = useState<"open" | "authenticated" | "institutional">("authenticated")
  const [review, setReview] = useState(false)
  const [busy, setBusy] = useState(false)
  const [blocked, setBlocked] = useState(false)
  const [message, setMessage] = useState("")
  const [error, setError] = useState("")
  const lock = useRef(false)
  const [lookup, setLookup] = useState<{ id: string; meeting: Schemas["MeetingOut"] | null; error: string } | null>(null)
  useEffect(() => {
    if (!sessionId) return
    const controller = new AbortController()
    setLookup(null)
    void api.GET("/api/v1/attendance-sessions/{session_id}/zoom/meeting", {
      params: { path: { session_id: sessionId } }, signal: controller.signal,
    }).then(result => {
      if (!controller.signal.aborted) setLookup({ id: sessionId, meeting: result.data ?? null, error: result.response.ok ? "" : errorMessage(result.error) })
    }).catch(() => {
      if (!controller.signal.aborted) setLookup({ id: sessionId, meeting: null, error: "No se pudo consultar la reunión." })
    })
    return () => controller.abort()
  }, [sessionId])
  const checked = lookup?.id === sessionId && !lookup.error && !lookup.meeting
  const valid = checked && sessions.some(s => s.id === sessionId) && !!topic.trim() &&
    Number.isFinite(Date.parse(start)) && Date.parse(start) > Date.now() &&
    Number.isInteger(Number(duration)) && Number(duration) >= 1 && Number(duration) <= 1440
  async function create() {
    if (!valid || !review || lock.current || blocked) return
    lock.current = true
    setBusy(true)
    setError("")
    try {
      const result = await api.POST("/api/v1/attendance-sessions/{session_id}/zoom/meeting", {
        params: { path: { session_id: sessionId } },
        body: { topic: topic.trim(), start_at: new Date(start).toISOString(), duration_minutes: Number(duration), authentication_mode: mode },
      })
      if (result.data) {
        setMessage("Reunión creada. Referencia Zoom: " + result.data.provider_id)
        setReview(false)
        setBlocked(true)
      } else {
        setError(errorMessage(result.error))
        if (result.response.status >= 500 || result.response.status === 409) setBlocked(true)
      }
    } catch {
      setError("Resultado no confirmado. Solicita revisión antes de repetir la creación.")
      setBlocked(true)
    } finally {
      lock.current = false
      setBusy(false)
    }
  }
  const disabled = busy || review || blocked
  return <section className="grid gap-3">
    <h3 className="font-semibold">Crear reunión Zoom</h3>
    <p className="text-sm">Disponible únicamente si la institución ha habilitado Zoom. La hora corresponde a la zona local del dispositivo.</p>
    {error && <Notice tone="warning" live="assertive">{error}</Notice>}
    {message && <Notice live="polite">{message}</Notice>}
    {blocked && <Notice>Consulta con administración antes de repetir una solicitud no confirmada. Para otra sesión, vuelve a abrir la pantalla.</Notice>}
    <Field label="Sesión académica" htmlFor="zoom-session">
      <select id="zoom-session" className={inputCls} disabled={disabled} value={sessionId} onChange={e => setSessionId(e.target.value)}>
        <option value="">Selecciona una sesión</option>
        {sessions.map(s => <option key={s.id} value={s.id}>{s.session_date} · {s.shift}</option>)}
      </select>
    </Field>
    {sessionId && lookup?.id !== sessionId && <Notice live="polite">Consultando reunión…</Notice>}
    {lookup?.id === sessionId && lookup.error && <Notice tone="warning">{lookup.error}</Notice>}
    {lookup?.id === sessionId && lookup.meeting && <Notice>Reunión existente: {lookup.meeting.provider_id} · {new Date(lookup.meeting.start_at).toLocaleString("es-ES")} · {lookup.meeting.duration_minutes} min</Notice>}
    <Field label="Tema" htmlFor="zoom-topic"><input id="zoom-topic" className={inputCls} maxLength={200} disabled={disabled} value={topic} onChange={e => setTopic(e.target.value)} /></Field>
    <Field label="Inicio (hora local)" htmlFor="zoom-start"><input id="zoom-start" type="datetime-local" className={inputCls} disabled={disabled} value={start} onChange={e => setStart(e.target.value)} /></Field>
    <Field label="Duración en minutos" htmlFor="zoom-duration"><input id="zoom-duration" type="number" min={1} max={1440} className={inputCls} disabled={disabled} value={duration} onChange={e => setDuration(e.target.value)} /></Field>
    <Field label="Acceso de participantes" htmlFor="zoom-mode">
      <select id="zoom-mode" className={inputCls} disabled={disabled} value={mode} onChange={e => setMode(e.target.value as typeof mode)}>
        <option value="authenticated">Cuenta Zoom autenticada</option>
        <option value="institutional">Perfil institucional</option>
        <option value="open">Sin cuenta Zoom</option>
      </select>
    </Field>
    {!review ? <Button disabled={!valid || disabled} onClick={() => setReview(true)}>Revisar reunión</Button> : <>
      <p className="text-sm">Confirma: {topic} · {new Date(start).toLocaleString("es-ES", { timeZoneName: "short" })} · {duration} min · {mode}</p>
      <Button disabled={!valid || busy || blocked} onClick={() => void create()}>Confirmar creación en Zoom</Button>
      <Button variant="ghost" disabled={busy || blocked} onClick={() => setReview(false)}>Editar</Button>
    </>}
  </section>
}
