import { useEffect, useRef, useState, type FormEvent } from 'react'
import { MessageSquareText, Send, Sparkles, Square, X } from 'lucide-react'
import { api, type Schemas } from '../../shared/api/client'
import { AssistantStreamError, streamAssistant } from '../../shared/api/assistantStream'
import { DocumentAnswer } from '../views/api/ApiAssistant'

type Exchange = { question: string; result: Schemas['AskOut'] }

export function AssistantWidget() {
  const [question, setQuestion] = useState('')
  const [cohort, setCohort] = useState('')
  const [cohorts, setCohorts] = useState<Schemas['AcademicCohortOut'][]>([])
  const [cohortStatus, setCohortStatus] = useState<'loading' | 'ready' | 'error'>('loading')
  const [messages, setMessages] = useState<Exchange[]>([])
  const [waiting, setWaiting] = useState('')
  const [partial, setPartial] = useState('')
  const [error, setError] = useState('')
  const [status, setStatus] = useState('')
  const dialog = useRef<HTMLDialogElement>(null)
  const launcher = useRef<HTMLButtonElement>(null)
  const input = useRef<HTMLTextAreaElement>(null)
  const end = useRef<HTMLDivElement>(null)
  const pending = useRef<AbortController | null>(null)

  useEffect(() => () => pending.current?.abort(), [])
  useEffect(() => {
    const controller = new AbortController()
    void api.GET('/api/v1/cohorts', { signal: controller.signal }).then(({ data }) => {
      if (controller.signal.aborted) return
      setCohorts(data ?? [])
      setCohortStatus(data ? 'ready' : 'error')
    }).catch(() => {
      if (!controller.signal.aborted) setCohortStatus('error')
    })
    return () => controller.abort()
  }, [])
  useEffect(() => {
    if (dialog.current?.open) end.current?.scrollIntoView({
      block: 'nearest',
      behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth',
    })
  }, [messages, waiting, partial, error])

  function stop() {
    const controller = pending.current
    if (!controller) return
    pending.current = null
    controller.abort()
    setQuestion(waiting)
    setWaiting('')
    setPartial('')
    setError('')
    setStatus('Consulta detenida.')
    input.current?.focus()
  }

  function clear() {
    pending.current?.abort()
    pending.current = null
    setStatus('')
    setMessages([])
    setWaiting('')
    setPartial('')
    setQuestion('')
    setError('')
  }

  async function ask(event: FormEvent) {
    event.preventDefault()
    const text = question.trim()
    if (pending.current || text.length < 3 || text.length > 500) return
    const controller = new AbortController()
    pending.current = controller
    input.current?.focus()
    setStatus('')
    setWaiting(text)
    setPartial('')
    setQuestion('')
    setError('')
    try {
      const result = await streamAssistant({ question: text, cohort_id: cohort.trim() || null }, controller.signal, {
        onPhase: () => {},
        onDelta: delta => {
          if (pending.current === controller) setPartial(previous => previous + delta)
        },
      })
      if (pending.current !== controller) return
      setMessages(previous => [...previous.slice(-9), { question: text, result }])
    } catch (cause) {
      if (pending.current === controller) {
        setError(cause instanceof AssistantStreamError ? cause.message : 'No se pudo consultar el asistente. Inténtalo de nuevo.')
        setQuestion(text)
      }
    } finally {
      if (pending.current === controller) {
        pending.current = null
        setWaiting('')
        setPartial('')
      }
    }
  }

  return (
    <>
      <button ref={launcher} type="button" aria-label="Abrir asistente EduGest" aria-haspopup="dialog"
        onClick={() => { dialog.current?.showModal(); input.current?.focus() }}
        className="fixed bottom-5 right-5 z-40 flex items-center gap-2 rounded-full bg-navy px-4 py-3 font-semibold text-white shadow-xl motion-safe:transition-transform motion-safe:hover:-translate-y-1">
        <MessageSquareText className="size-5 text-gold" aria-hidden /> Asistente
      </button>
      <dialog ref={dialog} aria-labelledby="floating-assistant-title" onClose={() => launcher.current?.focus()}
        className="fixed inset-auto bottom-3 right-3 m-0 w-[calc(100%-1.5rem)] max-w-md overflow-hidden rounded-2xl border border-line bg-white text-ink shadow-2xl backdrop:bg-navy/25 sm:bottom-6 sm:right-6 motion-safe:open:animate-[assistant-enter_200ms_ease-out]">
        <div className="flex h-[min(680px,calc(100dvh-1.5rem))] flex-col">
          <header className="flex shrink-0 items-center gap-3 bg-navy p-4 text-white">
            <Sparkles className="size-6 text-gold" aria-hidden />
            <div className="min-w-0 flex-1">
              <h2 id="floating-assistant-title" className="font-bold">EduGest IA</h2>
              <p className="text-xs text-gold">Asistente documental</p>
            </div>
            <button type="button" aria-label="Cerrar asistente" onClick={() => dialog.current?.close()} className="rounded-lg p-2 hover:bg-white/10 focus-visible:outline-gold">
              <X className="size-5" aria-hidden />
            </button>
          </header>
          <div className="flex items-center justify-between gap-2 border-b border-line px-4 py-2 text-xs">
            <span>Tu ámbito autorizado</span>
            <button type="button" onClick={clear} className="font-semibold text-blue hover:underline">Limpiar conversación</button>
          </div>
          <div className="shrink-0 border-b border-line px-4 py-2">
            <label htmlFor="floating-assistant-cohort" className="block text-xs font-semibold text-muted">Cohorte (opcional)</label>
            <select id="floating-assistant-cohort" value={cohort} disabled={!!waiting || cohortStatus !== 'ready'}
              onChange={event => { clear(); setCohort(event.target.value) }}
              className="mt-1 w-full rounded-lg border border-line px-2 py-1.5 text-sm">
              <option value="">Ámbito autorizado</option>
              {cohorts.map(item => <option key={item.id} value={item.id}>{item.nombre} · {item.id}</option>)}
            </select>
            {cohortStatus === 'loading' && <p role="status" className="mt-1 text-xs text-muted">Cargando cohortes…</p>}
            {cohortStatus === 'error' && <p role="status" className="mt-1 text-xs text-muted">No se pudo cargar la lista. Puedes consultar tu ámbito autorizado.</p>}
          </div>
          <div role="log" aria-label="Conversación del asistente" aria-live="polite" className="min-h-0 flex-1 space-y-4 overflow-y-auto overscroll-contain bg-canvas p-4">
            <p className="mr-6 rounded-2xl rounded-tl-sm border border-line bg-white p-3 text-sm">¡Hola! Pregúntame sobre la documentación de tu formación. Consultaré las fuentes autorizadas.</p>
            {messages.map((message, index) => (
              <article key={index} className="grid gap-2 break-words">
                <p className="ml-8 justify-self-end whitespace-pre-wrap rounded-2xl rounded-br-sm bg-navy px-4 py-3 text-white">{message.question}</p>
                <div className="mr-3 rounded-2xl rounded-tl-sm border border-line bg-white p-3"><DocumentAnswer result={message.result} /></div>
              </article>
            ))}
            {waiting && <>
              <p className="ml-8 whitespace-pre-wrap break-words rounded-2xl rounded-br-sm bg-navy px-4 py-3 text-white">{waiting}</p>
              {partial && <p className="mr-3 whitespace-pre-wrap break-words rounded-2xl border border-line bg-white p-3 text-sm">{partial}</p>}
              <div role="status" className="flex items-center gap-2 text-sm text-muted">
                <span aria-hidden className="flex gap-1">{[0, 1, 2].map(i => <span key={i} className="size-2 rounded-full bg-blue motion-safe:animate-pulse" style={{ animationDelay: `${i * 150}ms` }} />)}</span>
                {partial ? 'Recibiendo respuesta…' : 'Consultando fuentes…'}
              </div>
            </>}
            {error && <p role="alert" className="rounded-lg border border-line bg-white p-3 text-sm">{error}</p>}
            <div ref={end} />
          </div>
          <p role="status" className="sr-only">{status}</p>
          <form onSubmit={event => void ask(event)} className="shrink-0 border-t border-line p-3">
            <div className="flex items-end gap-2 rounded-xl border border-line p-2 focus-within:border-blue">
              <textarea ref={input} aria-label="Pregunta al asistente" placeholder="Escribe tu pregunta…" rows={2} maxLength={500} value={question}
                readOnly={!!waiting}
                onChange={event => setQuestion(event.target.value)}
                onKeyDown={event => { if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) { event.preventDefault(); if (!pending.current) event.currentTarget.form?.requestSubmit() } }}
                className="min-w-0 flex-1 resize-none bg-transparent p-1 text-sm" />
              {waiting ? (
                <button type="button" aria-label="Detener consulta" onClick={stop} className="rounded-xl bg-navy p-3 text-white">
                  <Square className="size-4" aria-hidden />
                </button>
              ) : (
                <button type="submit" aria-label="Enviar pregunta" disabled={question.trim().length < 3} className="rounded-xl bg-blue p-3 text-white disabled:opacity-40">
                  <Send className="size-4" aria-hidden />
                </button>
              )}
            </div>
            <p className="mt-2 text-xs text-muted">No envíes datos sensibles. Cada consulta es independiente; el historial no se guarda.</p>
          </form>
        </div>
      </dialog>
    </>
  )
}
