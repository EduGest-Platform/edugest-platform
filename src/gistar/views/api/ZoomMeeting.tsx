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
  const [providerId, setProviderId] = useState("")
  const [message, setMessage] = useState("")
  const [error, setError] = useState("")
  const lock = useRef(false)
  const [lookup, setLookup] = useState<{ id: string; meeting: Schemas["MeetingOut"] | null; intent: Schemas["ProvisioningOut"] | null; error: string } | null>(null)
  const [lookupAttempt, setLookupAttempt] = useState(0)
  useEffect(() => {
    if (!sessionId) return
    const controller = new AbortController()
    setLookup(null)
    const options = { params: { path: { session_id: sessionId } }, signal: controller.signal }
    void Promise.all([
      api.GET("/api/v1/attendance-sessions/{session_id}/zoom/meeting", options),
      api.GET("/api/v1/attendance-sessions/{session_id}/zoom/provisioning", options),
    ]).then(([meeting, intent]) => {
      const failure = !meeting.response.ok ? meeting : !intent.response.ok ? intent : null
      if (!controller.signal.aborted) setLookup({
        id: sessionId, meeting: meeting.data ?? null, intent: intent.data ?? null,
        error: failure ? errorMessage(failure.error) : "",
      })
    }).catch(() => {
      if (!controller.signal.aborted) setLookup({ id: sessionId, meeting: null, intent: null, error: "No se pudo consultar la reunión." })
    })
    return () => controller.abort()
  }, [sessionId, lookupAttempt])
  const [notes, setNotes] = useState<Schemas["NotesOut"][] | null>(null)
  const [notesError, setNotesError] = useState("")
  const [approving, setApproving] = useState(false)
  const approvalLock = useRef(false)
  const [notesAttempt, setNotesAttempt] = useState(0)
  const meetingId = lookup?.id === sessionId && lookup.meeting ? sessionId : ""
  useEffect(() => {
    setNotes(null)
    setNotesError("")
    if (!meetingId) return
    const controller = new AbortController()
    void api.GET("/api/v1/attendance-sessions/{session_id}/zoom/notes", {
      params: { path: { session_id: meetingId } }, signal: controller.signal,
    }).then(result => {
      if (controller.signal.aborted) return
      if (result.data) setNotes(result.data)
      else setNotesError(result.response.status === 404 ? "Notas no disponibles para esta reunión." : errorMessage(result.error))
    }).catch(() => {
      if (!controller.signal.aborted) setNotesError("No se pudieron consultar las notas.")
    })
    return () => controller.abort()
  }, [meetingId, notesAttempt])
  async function approveNote() {
    const latest = notes?.[0]
    if (!meetingId || !latest || latest.approved_at || approvalLock.current) return
    if (!window.confirm(`¿Aprobar la versión ${latest.version} de las notas de esta reunión?`)) return
    approvalLock.current = true
    setApproving(true)
    setNotesError("")
    try {
      const result = await api.POST("/api/v1/attendance-sessions/{session_id}/zoom/notes/approve", {
        params: { path: { session_id: meetingId } }, body: { expected_version: latest.version },
      })
      if (!result.data) setNotesError(errorMessage(result.error))
      else setNotes(previous => previous?.map(note => note.version === latest.version ? result.data! : note) ?? null)
    } catch {
      setNotesError("Resultado no confirmado. Actualiza las notas antes de volver a aprobar.")
    } finally {
      approvalLock.current = false
      setApproving(false)
    }
  }
  const checked = lookup?.id === sessionId && !lookup.error && !lookup.meeting && !lookup.intent
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
        setLookup({ id: sessionId, meeting: result.data, intent: null, error: "" })
      } else {
        setError(errorMessage(result.error))
        if (result.response.status >= 500 || result.response.status === 409 || result.response.status === 408) setBlocked(true)
      }
    } catch {
      setError("Resultado no confirmado. Solicita revisión antes de repetir la creación.")
      setBlocked(true)
    } finally {
      lock.current = false
      setBusy(false)
    }
  }
  const unresolved = lookup?.id === sessionId && !lookup.meeting ? lookup.intent : null
  async function reconcile() {
    if (!unresolved?.can_reconcile || lock.current || !/^[0-9]{1,32}$/.test(providerId)) return
    lock.current = true
    setBusy(true)
    setError("")
    try {
      const result = await api.POST("/api/v1/attendance-sessions/{session_id}/zoom/provisioning/reconcile", {
        params: { path: { session_id: sessionId } },
        body: { operation_id: unresolved.operation_id, provider_id: providerId },
      })
      if (result.data) {
        setLookup({ id: sessionId, meeting: result.data, intent: null, error: "" })
        setBlocked(false)
        setReview(false)
        setMessage("Reunión verificada y registrada.")
      } else setError(errorMessage(result.error))
    } catch {
      setError("No se pudo confirmar la conciliación. Consulta el registro de la reunión.")
    } finally {
      lock.current = false
      setBusy(false)
    }
  }
  const disabled = busy || review || blocked || approving
  const fieldsDisabled = disabled || !checked
  return <section className="grid gap-3">
    <h3 className="font-semibold">Gestionar reunión Zoom</h3>
    <p className="text-sm">Disponible únicamente si la institución ha habilitado Zoom. La hora corresponde a la zona local del dispositivo.</p>
    {error && <Notice tone="warning" live="assertive">{error}</Notice>}
    {message && <Notice live="polite">{message}</Notice>}
    {blocked && <>
      <Notice>Consulta con administración antes de repetir una solicitud no confirmada. Puedes comprobar si la reunión quedó registrada sin crear otra.</Notice>
      <Button variant="ghost" disabled={busy || lookup === null} onClick={() => { setLookup(null); setLookupAttempt(n => n + 1) }}>Comprobar registro de reunión</Button>
    </>}
    <Field label="Sesión académica" htmlFor="zoom-session">
      <select id="zoom-session" className={inputCls} disabled={disabled} value={sessionId} onChange={e => { setSessionId(e.target.value); setProviderId(""); setNotes(null); setNotesError(""); setLookup(null); setMessage(""); setError(""); setTopic(""); setStart(""); setDuration("60"); setMode("authenticated") }}>
        <option value="">Selecciona una sesión</option>
        {sessions.map(s => <option key={s.id} value={s.id}>{s.session_date} · {s.shift}</option>)}
      </select>
    </Field>
    {unresolved && <>
      <Notice tone="warning">Hay una solicitud de Zoom pendiente de conciliación. Referencia: {unresolved.operation_id}</Notice>
      <Button variant="ghost" disabled={busy} onClick={() => setLookupAttempt(n => n + 1)}>Actualizar estado de la solicitud</Button>
      {unresolved.can_reconcile && <div className="grid gap-2">
        <Field label="ID de la reunión existente en Zoom" htmlFor="zoom-provider-id">
          <input id="zoom-provider-id" className={inputCls} inputMode="numeric" maxLength={32}
            value={providerId} disabled={busy} onChange={event => setProviderId(event.target.value)} />
        </Field>
        <Button disabled={busy || !/^[0-9]{1,32}$/.test(providerId)} onClick={() => void reconcile()}>
          Verificar y registrar la reunión existente
        </Button>
      </div>}
    </>}
    {sessionId && lookup?.id !== sessionId && <Notice live="polite">Consultando reunión…</Notice>}
    {lookup?.id === sessionId && lookup.error && <>
      <Notice tone="warning">{lookup.error}</Notice>
      <Button variant="ghost" disabled={disabled} onClick={() => { setLookup(null); setLookupAttempt(n => n + 1) }}>Volver a consultar reunión</Button>
    </>}
    {blocked && lookup?.id === sessionId && !lookup.error && !lookup.meeting && !lookup.intent && <Notice tone="warning">No hay una reunión registrada localmente. Esto no descarta que Zoom haya aceptado la solicitud. No repitas la creación sin revisión.</Notice>}
    {lookup?.id === sessionId && lookup.meeting && <Notice>Reunión existente: {lookup.meeting.provider_id} · {new Date(lookup.meeting.start_at).toLocaleString("es-ES")} · {lookup.meeting.duration_minutes} min. No es necesario crear otra reunión para esta sesión.</Notice>}
    {meetingId && <section key={meetingId} className="grid gap-2 border-t border-line pt-3">
      <h4 className="font-semibold">Notas de reunión · revisión interna</h4>
      <Button variant="ghost" disabled={approving || (notes === null && !notesError)} onClick={() => { setNotes(null); setNotesError(""); setNotesAttempt(n => n + 1) }}>Actualizar notas</Button>
      {notesError && <Notice>{notesError}</Notice>}
      {notes === null && !notesError && <Notice live="polite">Consultando notas…</Notice>}
      {notes?.[0] && !notes[0].approved_at && !notesError && <Button disabled={approving} onClick={() => void approveNote()}>Aprobar última versión</Button>}
      {notes?.length === 0 && <Notice>No hay versiones de notas.</Notice>}
      {notes?.map(note => <details key={note.version} className="text-sm">
        <summary>Versión {note.version} · {note.approved_at ? "Aprobada" : "Borrador"}</summary>
        {([
          ["Resumen", note.body.summary],
          ["Temas principales", note.body.key_topics ?? []],
          ["Refuerzo", note.body.reinforcement_topics ?? []],
          ["Acciones propuestas", note.body.action_items ?? []],
        ] as const).map(([label, items]) => items.length > 0 && <section key={label} className="mt-3">
          <h5 className="font-semibold">{label}</h5>
          {items.map((item, index) => <div key={index} className="mt-2 break-words"><p>{item.text}</p><p className="text-xs text-muted">{item.evidence.map(span => `${span.start_seconds}–${span.end_seconds} s`).join(", ")}</p></div>)}
        </section>)}
      </details>)}
    </section>}
    <Field label="Tema" htmlFor="zoom-topic"><input id="zoom-topic" className={inputCls} maxLength={200} disabled={fieldsDisabled} value={topic} onChange={e => setTopic(e.target.value)} /></Field>
    <Field label="Inicio (hora local)" htmlFor="zoom-start"><input id="zoom-start" type="datetime-local" className={inputCls} disabled={fieldsDisabled} value={start} onChange={e => setStart(e.target.value)} /></Field>
    <Field label="Duración en minutos" htmlFor="zoom-duration"><input id="zoom-duration" type="number" min={1} max={1440} className={inputCls} disabled={fieldsDisabled} value={duration} onChange={e => setDuration(e.target.value)} /></Field>
    <Field label="Acceso de participantes" htmlFor="zoom-mode">
      <select id="zoom-mode" className={inputCls} disabled={fieldsDisabled} value={mode} onChange={e => setMode(e.target.value as typeof mode)}>
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
