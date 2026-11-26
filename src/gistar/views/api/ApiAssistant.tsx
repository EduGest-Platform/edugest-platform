import { BookOpen, ChartNoAxesCombined, Send, Sparkles, Square, Trash2, UserRound } from "lucide-react"
import { useEffect, useRef, useState, type FormEvent, type ReactNode } from "react"
import { AssistantStreamError, streamAssistant, type AssistantSource } from "../../../shared/api/assistantStream"
import type { Schemas } from "../../../shared/api/client"
import { useApiSession } from "../../../shared/api/session"
import { Button, Field, Notice, PageTitle, inputCls } from "../../ui"
import "./assistantChat.css"

type Answer = Schemas["AskOut"]
type Turn = { id: number; question: string; source?: AssistantSource; text: string; result?: Answer }

const participants = {
  assistant: { name: "Asistente EduGest", icon: Sparkles },
  documents: { name: "Asistente documental", icon: BookOpen },
  records: { name: "Asistente de registros", icon: ChartNoAxesCombined },
}

function ChatMessage({ name, avatar, own = false, children }: {
  name: string; avatar: ReactNode; own?: boolean; children: ReactNode
}) {
  return (
    <div className={`assistant-message flex items-start gap-2.5 sm:gap-3 ${own ? "flex-row-reverse" : ""}`}>
      <span aria-hidden="true" className={`grid size-9 shrink-0 place-items-center rounded-full text-xs font-bold ${own ? "bg-navy text-white" : "bg-mist text-navy"}`}>
        {avatar}
      </span>
      <div className={`min-w-0 max-w-[min(85%,45rem)] ${own ? "text-right" : ""}`}>
        <p className="mb-1.5 text-xs font-semibold text-muted">{name}</p>
        <div className={`wrap-anywhere rounded-2xl px-4 py-3 text-left text-sm leading-relaxed ${own
          ? "rounded-tr-sm bg-navy text-white"
          : "rounded-tl-sm border border-line bg-white text-ink"}`}>
          {children}
        </div>
      </div>
    </div>
  )
}

function WorkingDots() {
  return <span className="assistant-dots inline-flex items-center gap-1" aria-hidden="true">
    <span /><span /><span />
  </span>
}

export function DocumentAnswer({ result }: { result: Answer }) {
  // KAN-195: figures from the read-only tools. The server text already says "no hay registros" when there is no data.
  if (result.source_kind === "records")
    return (
      <div className="grid gap-3 text-sm">
        <p className="whitespace-pre-wrap wrap-anywhere">{result.answer}</p>
        {result.record && (
          <p className="text-xs text-muted">
            Registros operativos actuales · {result.record.tool} · fuente:{" "}
            {result.record.source} · consultado el {result.record.generated_at}
          </p>
        )}
        <p className="text-xs">
          Ámbito consultado:{" "}
          {result.scope_cohorts.join(", ") || "Sin cohortes indicadas"}
        </p>
      </div>
    )
  if (result.status === "no_source")
    return (
      <Notice>
        No consta en la documentación de tu ámbito. Consulta con tu equipo
        docente.
      </Notice>
    )
  return (
    <div className="grid gap-3 text-sm">
      <p className="whitespace-pre-wrap wrap-anywhere">{result.answer}</p>
      <p className="text-xs text-muted">
        Respuesta extractiva · búsqueda{" "}
        {result.retrieval === "hybrid" ? "híbrida" : "por palabras"} · vigencia
        comprobada a {result.as_of}
      </p>
      <p className="text-xs">
        Ámbito consultado:{" "}
        {result.scope_cohorts.join(", ") || "Sin cohortes indicadas"}
      </p>
      {result.citations.length ? (
        <ul className="grid gap-3" aria-label="Fuentes de la respuesta">
          {result.citations.map((citation, index) => (
            <li
              key={`${citation.source_key}:${index}`}
              className="rounded-lg border border-line p-3"
            >
              <h3 className="font-semibold">
                {citation.title} · {citation.version}
              </h3>
              <p className="text-xs">
                Referencia: {citation.source_key} · Desde {citation.valid_from}{" "}
                · Hasta {citation.valid_until ?? "Sin fecha de fin"}
              </p>
              <blockquote className="mt-2 whitespace-pre-wrap wrap-anywhere">
                {citation.excerpt}
              </blockquote>
            </li>
          ))}
        </ul>
      ) : (
        <Notice tone="warning">
          La respuesta no incluye citas. No la uses como evidencia documental.
        </Notice>
      )}
    </div>
  )
}

export function ApiAssistant() {
  const { me } = useApiSession()
  const initials = me?.display_name.trim().split(/\s+/u).slice(0, 2).map(word => Array.from(word)[0]).join("").toLocaleUpperCase("es")
  const [question, setQuestion] = useState("")
  const [cohort, setCohort] = useState("")
  const [messages, setMessages] = useState<Turn[]>([])
  const [active, setActive] = useState<Turn | null>(null)
  const [status, setStatus] = useState("")
  const [error, setError] = useState("")
  const [awayFromLatest, setAwayFromLatest] = useState(false)
  const pending = useRef<AbortController | null>(null)
  const nextId = useRef(0)
  const transcript = useRef<HTMLDivElement>(null)
  const questionInput = useRef<HTMLTextAreaElement>(null)
  const followLatest = useRef(true)

  useEffect(() => () => pending.current?.abort(), [])
  useEffect(() => {
    const panel = transcript.current
    if (panel && followLatest.current) panel.scrollTop = panel.scrollHeight
  }, [messages, active])

  function scrollToLatest() {
    followLatest.current = true
    setAwayFromLatest(false)
    const panel = transcript.current
    if (panel) panel.scrollTop = panel.scrollHeight
  }

  function stop() {
    pending.current?.abort()
    pending.current = null
    setActive(null)
    setStatus("Consulta detenida.")
    questionInput.current?.focus()
  }

  function clear() {
    stop()
    setMessages([])
    setQuestion("")
    setError("")
    setStatus("")
    scrollToLatest()
  }

  async function ask(event: FormEvent) {
    event.preventDefault()
    const text = question.trim()
    if (pending.current || text.length < 3 || text.length > 500) return

    questionInput.current?.focus({ preventScroll: true })
    const controller = new AbortController()
    pending.current = controller
    const id = ++nextId.current
    scrollToLatest()
    setActive({ id, question: text, text: "" })
    setError("")
    setStatus("Consultando las fuentes autorizadas…")

    try {
      const result = await streamAssistant({ question: text, cohort_id: cohort.trim() || null }, controller.signal, {
        onPhase: source => {
          setActive(turn => turn?.id === id ? { ...turn, source } : turn)
          if (pending.current === controller)
            setStatus(source === "records" ? "Consultando los registros autorizados…" : "Buscando en la documentación autorizada…")
        },
        onDelta: delta => setActive(turn => turn?.id === id ? { ...turn, text: turn.text + delta } : turn),
      })
      if (pending.current !== controller) return
      setMessages(previous => [...previous.slice(-9), { id, question: text, source: result.source_kind, text: "", result }])
      setQuestion("")
      setStatus("Consulta completada. Respuesta disponible en la conversación.")
    } catch (cause) {
      if (pending.current !== controller) return
      setStatus("")
      setError(cause instanceof AssistantStreamError ? cause.message : "No se pudo consultar el asistente. Vuelve a intentarlo.")
    } finally {
      if (pending.current === controller) {
        pending.current = null
        setActive(null)
      }
    }
  }

  const busy = active !== null
  const turns = active ? [...messages.slice(-9), active] : messages

  return (
    <div className="mx-auto w-full max-w-5xl">
      <PageTitle title="Asistente EduGest" sub="Consulta la documentación del curso y los registros de tu ámbito." />
      <section aria-label="Chat de EduGest" className="overflow-hidden rounded-3xl border border-line bg-white shadow-sm">
        <header className="flex flex-wrap items-center justify-between gap-3 border-b border-line px-4 py-3.5 sm:px-6">
          <h2 className="font-semibold text-navy">Conversación</h2>
          <Button variant="ghost" size="sm" onClick={clear} disabled={!busy && !messages.length && !question && !error}>
            <Trash2 className="size-4" aria-hidden /> Limpiar conversación
          </Button>
        </header>
        <div
          ref={transcript}
          className="assistant-transcript grid content-start gap-5 overflow-y-auto overscroll-contain bg-canvas px-4 py-5 sm:px-6"
          role="region"
          aria-label="Mensajes de la conversación"
          tabIndex={0}
          onScroll={event => {
            const { scrollTop, clientHeight, scrollHeight } = event.currentTarget
            followLatest.current = scrollHeight - scrollTop - clientHeight < 48
            setAwayFromLatest(!followLatest.current)
          }}
        >
          {!turns.length && (
            <div className="my-10 text-center text-sm text-muted">
              <Sparkles className="mx-auto mb-3 size-6 text-blue" aria-hidden />
              Escribe una pregunta sobre tu formación para empezar.
            </div>
          )}
          {turns.map(turn => {
            const { name, icon: Avatar } = participants[turn.source ?? "assistant"]
            return (
              <article key={turn.id} className="grid gap-4" aria-label="Intercambio de mensajes">
                <ChatMessage name="Tú" own avatar={initials || <UserRound className="size-4" />}>
                  <p className="whitespace-pre-wrap">{turn.question}</p>
                </ChatMessage>
                <ChatMessage name={name} avatar={<Avatar className="size-4" />}>
                  {turn.result ? <DocumentAnswer result={turn.result} /> : (
                    <>
                      {turn.text && <p className="mb-2 whitespace-pre-wrap">{turn.text}</p>}
                      <div className="flex items-center gap-2 text-xs text-muted">
                        <WorkingDots /> {turn.text ? "Recibiendo respuesta…" : "Consultando…"}
                      </div>
                    </>
                  )}
                </ChatMessage>
              </article>
            )
          })}
        </div>
        <div className="border-t border-line px-4 py-4 sm:px-6">
          {awayFromLatest && <Button size="sm" variant="ghost" onClick={scrollToLatest}>Ir al último mensaje</Button>}
          <p role="status" className="sr-only">{status}</p>
          {error && <Notice tone="warning" live="assertive">{error}</Notice>}
          <form onSubmit={event => void ask(event)} className="grid gap-3">
            <Field label="ID de cohorte (opcional)" htmlFor="assistant-cohort">
              <input id="assistant-cohort" className={`${inputCls} sm:max-w-xs`} maxLength={20} value={cohort}
                readOnly={busy} onChange={event => setCohort(event.target.value)} />
            </Field>
            <Field label="Tu pregunta" htmlFor="assistant-question">
              <textarea ref={questionInput} id="assistant-question" className={`${inputCls} assistant-composer resize-y`}
                minLength={3} maxLength={500} required rows={2} value={question} readOnly={busy}
                onChange={event => setQuestion(event.target.value)} />
            </Field>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="text-xs text-muted">Evita compartir datos sensibles. Los mensajes se conservan solo en esta vista.</p>
              {busy ? (
                <Button variant="ghost" onClick={stop}><Square className="size-4" aria-hidden /> Detener consulta</Button>
              ) : (
                <Button type="submit" className="assistant-chat-action" disabled={question.trim().length < 3}>
                  <Send className="size-4" aria-hidden /> Enviar
                </Button>
              )}
            </div>
          </form>
        </div>
      </section>
    </div>
  )
}
