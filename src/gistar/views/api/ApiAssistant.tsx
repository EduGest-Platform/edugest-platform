import { useEffect, useRef, useState, type FormEvent } from "react"
import { api, type Schemas } from "../../../shared/api/client"
import { describeApiError, problemText } from "../../../shared/api/errors"
import { Button, Card, Field, Notice, PageTitle, inputCls } from "../../ui"

type Answer = Schemas["AskOut"]
type Message = {
  question: string
  result: Answer
}

export function DocumentAnswer({ result }: { result: Answer }) {
  if (result.status === "no_source")
    return (
      <Notice>
        No consta en la documentación de tu ámbito. Consulta con tu equipo
        docente.
      </Notice>
    )
  return (
    <div className="grid gap-3 text-sm">
      <p className="whitespace-pre-wrap">{result.answer}</p>
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
              <blockquote className="mt-2 whitespace-pre-wrap">
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
  const [question, setQuestion] = useState("")
  const [cohort, setCohort] = useState("")
  const [messages, setMessages] = useState<Message[]>([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState("")
  const pending = useRef<AbortController | null>(null)
  const generation = useRef(0)
  useEffect(
    () => () => {
      generation.current++
      pending.current?.abort()
    },
    [],
  )
  const clear = () => {
    generation.current++
    pending.current?.abort()
    pending.current = null
    setBusy(false)
    setMessages([])
    setQuestion("")
    setError("")
  }
  const ask = async (event: FormEvent) => {
    event.preventDefault()
    const text = question.trim()
    if (pending.current || text.length < 3 || text.length > 500) return
    const controller = new AbortController()
    pending.current = controller
    const current = ++generation.current
    setBusy(true)
    setError("")
    try {
      const {
        data,
        error: apiError,
        response,
      } = await api.POST("/api/v1/assistant/ask", {
        body: { question: text, cohort_id: cohort.trim() || null },
        signal: controller.signal,
      })
      if (controller.signal.aborted || current !== generation.current) return
      if (!data) {
        setError(problemText(describeApiError(response.status, apiError)))
        return
      }
      setMessages((previous) => [
        ...previous.slice(-9),
        { question: text, result: data },
      ])
      setQuestion("")
    } catch {
      if (!controller.signal.aborted && current === generation.current)
        setError(
          "No se pudo consultar el asistente. No se ha generado una respuesta local.",
        )
    } finally {
      if (current === generation.current) {
        pending.current = null
        setBusy(false)
      }
    }
  }
  return (
    <>
      <PageTitle
        title="Asistente documental"
        sub="Consulta al backend con citas y abstención. Respuestas extractivas; no son generación libre ni una predicción."
      />
      <Card
        title="Documentación de tu ámbito"
        action={
          <Button variant="ghost" onClick={clear}>
            Limpiar conversación
          </Button>
        }
      >
        <Notice>
          El servidor determina tus permisos y la vigencia de las fuentes. No
          envíes datos personales sensibles. Solo se conservan en esta vista los
          últimos diez intercambios; no se guardan en el navegador ni se envía
          el historial.
        </Notice>
        <div className="grid gap-5" aria-label="Conversación documental">
          {!messages.length && (
            <p className="text-sm text-muted">Todavía no hay consultas.</p>
          )}
          {messages.map((message, index) => (
            <article key={index} className="grid gap-3 rounded-xl bg-mist p-4">
              <h2 className="whitespace-pre-wrap font-semibold">
                {message.question}
              </h2>
              <DocumentAnswer result={message.result} />
            </article>
          ))}
        </div>
        {error && (
          <Notice tone="warning" live="assertive">
            {error}
          </Notice>
        )}
        {busy && (
          <Notice live="polite">Consultando las fuentes autorizadas…</Notice>
        )}
        {!busy && messages.length > 0 && (
          <p role="status" className="mt-3 text-sm">
            Consulta completada. Respuesta y fuentes disponibles en la
            conversación.
          </p>
        )}
        <form onSubmit={(e) => void ask(e)} className="mt-5 grid gap-3">
          <Field
            label="ID de cohorte (opcional; vacío consulta tu ámbito autorizado)"
            htmlFor="assistant-cohort"
          >
            <input
              id="assistant-cohort"
              className={inputCls}
              maxLength={20}
              value={cohort}
              disabled={busy}
              onChange={(e) => setCohort(e.target.value)}
            />
          </Field>
          <Field label="Pregunta documental" htmlFor="assistant-question">
            <textarea
              id="assistant-question"
              className={inputCls}
              minLength={3}
              maxLength={500}
              required
              value={question}
              disabled={busy}
              onChange={(e) => setQuestion(e.target.value)}
            />
          </Field>
          <Button type="submit" disabled={busy || question.trim().length < 3}>
            Consultar documentación
          </Button>
        </form>
      </Card>
    </>
  )
}
