import { useState, type FormEvent } from 'react'
import { BookText, CornerDownLeft, Sparkles, X } from 'lucide-react'
import { useGistar } from '../store'
import { Button, Card, Notice, PageTitle, inputCls } from '../ui'

interface Msg {
  q: string
  a: string
  doc?: string
  section?: string
}

export function Assistant() {
  const { data } = useGistar()
  const [chat, setChat] = useState<Msg[]>([])
  const [question, setQuestion] = useState('')
  const [source, setSource] = useState<{ doc: string; section: string } | null>(null)

  const ask = (q: string) => {
    const r = data.respuestas_rag_mock.find((x) => x.pregunta.toLowerCase() === q.trim().toLowerCase())
    setChat((c) => [
      ...c,
      r
        ? { q: r.pregunta, a: r.respuesta, doc: r.doc_id, section: r.seccion_id }
        : { q, a: 'No encuentro esa información en los documentos disponibles. Consulta con una persona del equipo docente.' },
    ])
  }
  const submit = (e: FormEvent) => {
    e.preventDefault()
    if (!question.trim()) return
    ask(question)
    setQuestion('')
  }
  const doc = source && data.documentos.find((d) => d.id === source.doc)
  const section = doc?.secciones.find((s) => s.id === source?.section)

  return (
    <>
      <PageTitle title="Pregunta a Gistar" sub="Asistente documental simulado · respuestas con citas a documentos ficticios." />
      <div className="grid gap-5 lg:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]">
        <Card title="Chat documental">
          <Notice>No existe conexión a un LLM ni búsqueda vectorial real. Las respuestas son deterministas.</Notice>
          <div className="mb-5 flex flex-wrap gap-2">
            {data.respuestas_rag_mock.map((r) => (
              <button
                key={r.clave}
                type="button"
                onClick={() => ask(r.pregunta)}
                className="cursor-pointer rounded-full border border-line bg-white px-3.5 py-1.5 text-left text-[13px] text-[#255c81] transition-colors hover:border-blue/40 hover:bg-mist"
              >
                {r.pregunta}
              </button>
            ))}
          </div>
          <div className="grid min-h-40 content-start gap-4 rounded-xl bg-mist/50 p-4">
            {chat.length === 0 && <p className="m-auto text-sm text-muted">Selecciona una pregunta o escribe una nueva.</p>}
            {chat.map((c, i) => (
              <div key={i} className="grid gap-2">
                <p className="ml-auto max-w-[85%] rounded-2xl rounded-br-md bg-navy px-4 py-2.5 text-sm text-white">{c.q}</p>
                <div className="mr-auto max-w-[85%] rounded-2xl rounded-bl-md border border-line bg-white px-4 py-2.5 text-sm">
                  <p className="flex gap-2">
                    <Sparkles className="mt-0.5 size-3.5 shrink-0 text-gold" aria-hidden />
                    {c.a}
                  </p>
                  {c.doc && (
                    <button
                      type="button"
                      onClick={() => setSource({ doc: c.doc!, section: c.section! })}
                      className="mt-2 inline-flex cursor-pointer items-center gap-1.5 text-xs font-semibold text-blue hover:underline"
                    >
                      <BookText className="size-3.5" aria-hidden /> Fuente: {c.doc} · {c.section}
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
          <form onSubmit={submit} className="mt-4 flex gap-2">
            <input aria-label="Tu pregunta" className={inputCls} placeholder="Pregunta sobre el programa…" value={question} onChange={(e) => setQuestion(e.target.value)} />
            <Button type="submit" aria-label="Preguntar">
              <CornerDownLeft className="size-4" aria-hidden /> Preguntar
            </Button>
          </form>
        </Card>
        <Card
          title="Documento fuente"
          className="lg:self-start"
          action={
            doc && (
              <Button size="sm" variant="subtle" aria-label="Cerrar fuente" onClick={() => setSource(null)}>
                <X className="size-4" aria-hidden />
              </Button>
            )
          }
        >
          {doc ? (
            <div className="text-sm">
              <p className="font-mono text-xs text-muted">{doc.id}</p>
              <h3 className="mb-3 mt-1 text-base font-semibold">{doc.titulo}</h3>
              <div className="rounded-xl border-l-4 border-teal bg-teal-50/60 px-4 py-3">
                <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-teal-800">{section?.titulo ?? 'Sin sección'}</p>
                <p className="leading-relaxed">{section?.contenido}</p>
              </div>
            </div>
          ) : (
            <p className="text-sm text-muted">Pulsa en la fuente de una respuesta para ver el fragmento citado.</p>
          )}
        </Card>
      </div>
    </>
  )
}
