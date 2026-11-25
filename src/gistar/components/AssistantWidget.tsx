import { useEffect, useRef, useState, type FormEvent } from 'react'
import { MessageSquareText, Send, Sparkles, X } from 'lucide-react'
import type { Schemas } from '../../shared/api/client'
import { askAssistant } from '../views/api/askAssistant'
import { describeApiError, problemText } from '../../shared/api/errors'
import { DocumentAnswer } from '../views/api/ApiAssistant'

type Exchange = { question: string; result: Schemas['AskOut'] }

export function AssistantWidget() {
  const [question, setQuestion] = useState('')
  const [messages, setMessages] = useState<Exchange[]>([])
  const [waiting, setWaiting] = useState('')
  const [error, setError] = useState('')
  const dialog = useRef<HTMLDialogElement>(null)
  const launcher = useRef<HTMLButtonElement>(null)
  const input = useRef<HTMLTextAreaElement>(null)
  const end = useRef<HTMLDivElement>(null)
  const pending = useRef<AbortController | null>(null)

  useEffect(() => () => pending.current?.abort(), [])
  useEffect(() => {
    if (dialog.current?.open) end.current?.scrollIntoView({
      block: 'nearest',
      behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth',
    })
  }, [messages, waiting, error])

  function clear() {
    pending.current?.abort()
    pending.current = null
    setMessages([])
    setWaiting('')
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
    setWaiting(text)
    setQuestion('')
    setError('')
    try {
      const { data, error: apiError, response } = await askAssistant(text, controller.signal)
      if (controller.signal.aborted) return
      if (data) setMessages(previous => [...previous.slice(-9), { question: text, result: data }])
      else {
        setError(problemText(describeApiError(response.status, apiError)))
        setQuestion(text)
      }
    } catch {
      if (!controller.signal.aborted) {
        setError('No se pudo consultar el asistente. Inténtalo de nuevo.')
        setQuestion(text)
      }
    } finally {
      if (pending.current === controller) {
        pending.current = null
        setWaiting('')
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
              <div role="status" className="flex items-center gap-2 text-sm text-muted">
                <span aria-hidden className="flex gap-1">{[0, 1, 2].map(i => <span key={i} className="size-2 rounded-full bg-blue motion-safe:animate-pulse" style={{ animationDelay: `${i * 150}ms` }} />)}</span>
                Consultando fuentes…
              </div>
            </>}
            {error && <p role="alert" className="rounded-lg border border-line bg-white p-3 text-sm">{error}</p>}
            <div ref={end} />
          </div>
          <form onSubmit={event => void ask(event)} className="shrink-0 border-t border-line p-3">
            <div className="flex items-end gap-2 rounded-xl border border-line p-2 focus-within:border-blue">
              <textarea ref={input} aria-label="Pregunta al asistente" placeholder="Escribe tu pregunta…" rows={2} maxLength={500} value={question}
                readOnly={!!waiting}
                onChange={event => setQuestion(event.target.value)}
                onKeyDown={event => { if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) { event.preventDefault(); if (!pending.current) event.currentTarget.form?.requestSubmit() } }}
                className="min-w-0 flex-1 resize-none bg-transparent p-1 text-sm" />
              <button type="submit" aria-label="Enviar pregunta" disabled={!!waiting || question.trim().length < 3} className="rounded-xl bg-blue p-3 text-white disabled:opacity-40">
                <Send className="size-4" aria-hidden />
              </button>
            </div>
            <p className="mt-2 text-xs text-muted">No envíes datos sensibles. Cada consulta es independiente; el historial no se guarda.</p>
          </form>
        </div>
      </dialog>
    </>
  )
}
