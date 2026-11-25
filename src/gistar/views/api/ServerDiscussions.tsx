import { useCallback, useEffect, useId, useState } from 'react'
import { api, type Schemas } from '../../../shared/api/client'
import { describeApiError, problemText } from '../../../shared/api/errors'
import { useApiSession } from '../../../shared/api/session'
import { Button, Empty, Field, Notice, inputCls } from '../../ui'

type Thread = Schemas['ThreadOut']
type Comment = Schemas['CommentOut']
type Resource<T> = { data?: T; error?: unknown; response: Response }
type ReadState<T> = { data: T } | { error: string } | null

const PAGE_SIZE = 20
const formatTime = new Intl.DateTimeFormat('es-ES', {
  dateStyle: 'medium', timeStyle: 'short', timeZone: 'Europe/Madrid',
})

function useDiscussionRead<T>(read: (signal: AbortSignal) => Promise<Resource<T>>) {
  const [state, setState] = useState<ReadState<T>>(null)
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    setState(null)
    void read(controller.signal).then(({ data, error, response }) => {
      if (controller.signal.aborted) return
      setState(data === undefined ? { error: problemText(describeApiError(response.status, error)) } : { data })
    }).catch(() => {
      if (!controller.signal.aborted) setState({ error: 'No se pudo conectar con el servidor.' })
    })
    return () => controller.abort()
  }, [read, attempt])

  return {
    state,
    refresh() {
      setState(null)
      setAttempt(previous => previous + 1)
    },
  }
}

function DiscussionReadError({ message, retry }: { message: string; retry: () => void }) {
  return (
    <div className="grid justify-items-start gap-2">
      <Notice tone="warning" live="polite">{message}</Notice>
      <Button size="sm" variant="ghost" onClick={retry}>Reintentar</Button>
    </div>
  )
}

function PageControls({ label, offset, total, onPage }: {
  label: string
  offset: number
  total: number
  onPage: (offset: number) => void
}) {
  if (total <= PAGE_SIZE) return null
  return (
    <nav aria-label={label} className="flex flex-wrap items-center gap-2 text-xs text-muted">
      <Button size="sm" variant="ghost" disabled={offset === 0} onClick={() => onPage(offset - PAGE_SIZE)}>Anterior</Button>
      <span>{offset + 1}–{Math.min(offset + PAGE_SIZE, total)} de {total}</span>
      <Button size="sm" variant="ghost" disabled={offset + PAGE_SIZE >= total} onClick={() => onPage(offset + PAGE_SIZE)}>Siguiente</Button>
    </nav>
  )
}

function CommentContent({ comment, userId }: { comment: Comment; userId?: string }) {
  const created = formatTime.format(new Date(comment.created_at))
  const author = comment.actor_user_id === userId ? 'Tú' : 'Equipo'
  return (
    <>
      <p className="text-xs text-muted">
        {author} · <time dateTime={comment.created_at}>{created}</time>
        {comment.parent_id && ' · Respuesta'}
        {comment.edited_at && comment.body !== null && ' · Editado'}
      </p>
      <p className="mt-1 whitespace-pre-wrap break-words">
        {comment.body ?? 'Comentario eliminado'}
      </p>
    </>
  )
}

function ThreadComments({ thread }: { thread: Thread }) {
  const { me } = useApiSession()
  const [offset, setOffset] = useState(0)
  const read = useCallback((signal: AbortSignal) => api.GET('/api/v1/discussion-threads/{thread_id}/comments', {
    params: { path: { thread_id: thread.id }, query: { limit: PAGE_SIZE, offset } },
    signal,
  }), [thread.id, offset])
  const { state, refresh } = useDiscussionRead(read)

  if (!state) return <p role="status" className="text-sm text-muted">Cargando comentarios…</p>
  if ('error' in state) return <DiscussionReadError message={state.error} retry={refresh} />
  const { items, total } = state.data
  return (
    <div className="space-y-3">
      <p className="text-xs text-muted">{thread.resolved_at ? 'Hilo resuelto' : 'Hilo abierto'}</p>
      {items.length === 0 ? <Empty>El hilo todavía no tiene comentarios.</Empty> : (
        <ol aria-label="Comentarios del hilo" className="grid gap-2">
          {items.map(comment => (
            <li key={comment.id} className={`rounded-lg border border-line p-3 ${comment.parent_id ? 'ml-3 border-l-2' : ''}`}>
              <CommentContent comment={comment} userId={me?.id} />
            </li>
          ))}
        </ol>
      )}
      <PageControls label="Páginas de comentarios" offset={offset} total={total} onPage={setOffset} />
    </div>
  )
}

function ApplicationDiscussions({ applicationId }: { applicationId: string }) {
  const [offset, setOffset] = useState(0)
  const [selection, setSelection] = useState('')
  const threadSelectId = useId()
  const read = useCallback((signal: AbortSignal) => api.GET('/api/v1/discussion-threads', {
    params: { query: { scope_type: 'application', application_id: applicationId, limit: PAGE_SIZE, offset } },
    signal,
  }), [applicationId, offset])
  const { state, refresh } = useDiscussionRead(read)

  if (!state) return <p role="status" className="text-sm text-muted">Cargando hilos…</p>
  if ('error' in state) return <DiscussionReadError message={state.error} retry={refresh} />
  const { items, total } = state.data
  if (!items.length) return <Empty>Este expediente todavía no tiene hilos.</Empty>
  const thread = items.find(item => item.id === selection) ?? items[0]
  return (
    <div className="space-y-3">
      <Field label="Hilo" htmlFor={threadSelectId}>
        <select id={threadSelectId} value={thread.id} className={inputCls} onChange={event => setSelection(event.target.value)}>
          {items.map(item => <option key={item.id} value={item.id}>{item.subject}</option>)}
        </select>
      </Field>
      <PageControls label="Páginas de hilos" offset={offset} total={total} onPage={setOffset} />
      <ThreadComments key={thread.id} thread={thread} />
    </div>
  )
}

export function ServerDiscussions({ applicationId }: { applicationId: string }) {
  const [opened, setOpened] = useState(false)
  return (
    <details className="rounded-xl border border-line p-3" onToggle={event => {
      if (event.currentTarget.open) setOpened(true)
    }}>
      <summary className="cursor-pointer font-semibold">Comentarios internos</summary>
      {opened && <div className="mt-3"><ApplicationDiscussions applicationId={applicationId} /></div>}
    </details>
  )
}
