import { useCallback, useEffect, useId, useRef, useState, type FormEvent } from 'react'
import { api, type Schemas } from '../../../shared/api/client'
import { describeApiError, problemText } from '../../../shared/api/errors'
import { useApiSession } from '../../../shared/api/session'
import { Button, Empty, Field, Notice, inputCls } from '../../ui'

type Thread = Schemas['ThreadOut']
type Comment = Schemas['CommentOut']
type Resource<T> = { data?: T; error?: unknown; response: Response }
type ReadState<T> = { data: T } | { error: string } | null
type WriteError = { message: string; status?: number; code?: string }

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

function useDiscussionWrite() {
  const lock = useRef(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<WriteError | null>(null)

  async function save<T>(write: () => Promise<Resource<T>>): Promise<T | undefined> {
    if (lock.current) return
    lock.current = true
    setBusy(true)
    setError(null)
    try {
      const result = await write()
      if (result.data !== undefined) return result.data
      const code = result.error && typeof result.error === 'object' && 'code' in result.error
        ? result.error.code : undefined
      setError({
        message: problemText(describeApiError(result.response.status, result.error)),
        status: result.response.status,
        code: typeof code === 'string' ? code : undefined,
      })
    } catch {
      setError({ message: 'No se pudo confirmar el cambio. Revisa el hilo antes de volver a intentarlo.' })
    } finally {
      lock.current = false
      setBusy(false)
    }
  }

  return { save, busy, error, clearError: () => setError(null) }
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

function ThreadComments({ threadId, onDirty }: { threadId: string; onDirty: (dirty: boolean) => void }) {
  const { me } = useApiSession()
  const [offset, setOffset] = useState(0)
  const [body, setBody] = useState('')
  const [parent, setParent] = useState<Comment | null>(null)
  const [editing, setEditing] = useState<Comment | null>(null)
  const [notice, setNotice] = useState('')
  const commentId = useId()
  const textarea = useRef<HTMLTextAreaElement>(null)
  const { save, busy, error, clearError } = useDiscussionWrite()

  useEffect(() => {
    onDirty(Boolean(body.trim()) || Boolean(editing) || busy)
  }, [body, editing, busy, onDirty])

  const read = useCallback(async (signal: AbortSignal): Promise<Resource<{ thread: Thread; comments: Schemas['CommentList'] }>> => {
    const path = { thread_id: threadId }
    const [thread, comments] = await Promise.all([
      api.GET('/api/v1/discussion-threads/{thread_id}', { params: { path }, signal }),
      api.GET('/api/v1/discussion-threads/{thread_id}/comments', {
        params: { path, query: { limit: PAGE_SIZE, offset } }, signal,
      }),
    ])
    if (!thread.data) return { response: thread.response, error: thread.error }
    if (!comments.data) return { response: comments.response, error: comments.error }
    return { response: comments.response, data: { thread: thread.data, comments: comments.data } }
  }, [threadId, offset])
  const { state, refresh } = useDiscussionRead(read)
  const conflict = error?.status === 409 || error?.code === 'parent_not_found'
  const staleEdit = error?.code === 'stale_comment'
  const latest = state && 'data' in state && editing
    ? state.data.comments.items.find(item => item.id === editing.id)
    : undefined
  const differentRevision = Boolean(editing && latest && latest.version !== editing.version)

  function refreshThread() {
    if (!staleEdit || differentRevision) clearError()
    setNotice('')
    refresh()
  }

  function discardDraft() {
    setEditing(null)
    setParent(null)
    setBody('')
    clearError()
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!body.trim() || !state || 'error' in state || state.data.thread.resolved_at || conflict || differentRevision) return
    setNotice('')
    const text = body.trim()
    const saved = await save(() => editing
      ? api.PATCH('/api/v1/discussion-comments/{comment_id}', {
        params: { path: { comment_id: editing.id } },
        body: { body: text, expected_version: editing.version },
      })
      : api.POST('/api/v1/discussion-threads/{thread_id}/comments', {
        params: { path: { thread_id: threadId } },
        body: { body: text, parent_id: parent?.id },
      }))
    if (!saved) return
    setBody('')
    setParent(null)
    setEditing(null)
    setNotice(editing ? 'Comentario actualizado.' : 'Comentario guardado.')
    if (!editing) setOffset(Math.floor(state.data.comments.total / PAGE_SIZE) * PAGE_SIZE)
    refresh()
  }

  async function changeResolution(thread: Thread) {
    const resolved = !thread.resolved_at
    setNotice('')
    const saved = await save(() => api.POST('/api/v1/discussion-threads/{thread_id}/resolution', {
      params: { path: { thread_id: threadId } },
      body: { resolved, expected_version: thread.version },
    }))
    if (saved) {
      setNotice(resolved ? 'Hilo resuelto.' : 'Hilo reabierto.')
      refresh()
    }
  }

  if (!state) return <p role="status" className="text-sm text-muted">Cargando comentarios…</p>
  if ('error' in state) return <DiscussionReadError message={state.error} retry={refresh} />
  const { thread, comments: { items, total } } = state.data
  const drafting = Boolean(body.trim()) || Boolean(editing)
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs text-muted">{thread.resolved_at ? 'Hilo resuelto' : 'Hilo abierto'}</p>
        <div className="flex flex-wrap gap-2">
          <Button size="sm" variant="ghost" disabled={busy} onClick={refreshThread}>Actualizar hilo</Button>
          {thread.created_by === me?.id && (
            <Button size="sm" variant="ghost" disabled={busy || conflict || (drafting && !thread.resolved_at)}
              onClick={() => void changeResolution(thread)}>
              {thread.resolved_at ? 'Reabrir hilo' : 'Resolver hilo'}
            </Button>
          )}
        </div>
      </div>
      {items.length === 0 ? <Empty>El hilo todavía no tiene comentarios.</Empty> : (
        <ol aria-label="Comentarios del hilo" className="grid gap-2">
          {items.map(comment => (
            <li key={comment.id} className={`rounded-lg border border-line p-3 ${comment.parent_id ? 'ml-3 border-l-2' : ''}`}>
              <CommentContent comment={comment} userId={me?.id} />
              {!thread.resolved_at && comment.body !== null && (
                <div className="mt-1 flex flex-wrap gap-1">
                  <Button size="sm" variant="subtle" disabled={busy || drafting} onClick={() => {
                    clearError()
                    setParent(comment)
                    textarea.current?.focus()
                  }}>Responder</Button>
                  {comment.actor_user_id === me?.id && (
                    <Button size="sm" variant="subtle" disabled={busy || drafting} onClick={() => {
                      clearError()
                      setParent(null)
                      setEditing(comment)
                      setBody(comment.body ?? '')
                      textarea.current?.focus()
                    }}>Editar comentario</Button>
                  )}
                </div>
              )}
            </li>
          ))}
        </ol>
      )}
      {!drafting && !busy && <PageControls label="Páginas de comentarios" offset={offset} total={total} onPage={setOffset} />}
      {notice && <p role="status" className="text-sm">{notice}</p>}
      {error && <Notice tone="warning" live="polite">{error.message}</Notice>}
      {differentRevision && latest?.body != null && (
        <div className="grid justify-items-start gap-2 rounded-lg border border-line p-3">
          <p className="text-sm font-semibold">Versión actual del comentario</p>
          <p className="whitespace-pre-wrap break-words text-sm">{latest.body}</p>
          <Button size="sm" variant="ghost" onClick={() => {
            setEditing(latest)
            clearError()
            textarea.current?.focus()
          }}>Conservar mi borrador y usar esta versión</Button>
        </div>
      )}
      {differentRevision && latest?.body === null && <Notice tone="warning" live="polite">El comentario se eliminó. Puedes copiar tu borrador.</Notice>}
      {(!thread.resolved_at || drafting) && (
        <form className="grid justify-items-start gap-2" onSubmit={submit}>
          {parent && (
            <div className="w-full rounded-lg border-l-2 border-line bg-mist p-2">
              <p className="text-xs font-semibold">En respuesta a</p>
              <p className="line-clamp-2 whitespace-pre-wrap break-words text-xs">{parent.body}</p>
              <Button size="sm" variant="subtle" disabled={busy} onClick={() => {
                setParent(null)
                clearError()
              }}>Quitar respuesta</Button>
            </div>
          )}
          <div className="w-full">
            <Field label={editing ? 'Editar tu comentario' : parent ? 'Tu respuesta' : 'Nuevo comentario'} htmlFor={commentId}>
              <textarea id={commentId} ref={textarea} rows={3} maxLength={2000} value={body} disabled={busy}
                onChange={event => setBody(event.target.value)} className={inputCls} />
            </Field>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button size="sm" type="submit" disabled={busy || !body.trim() || conflict || differentRevision || Boolean(thread.resolved_at)}>
              {editing ? 'Guardar edición' : parent ? 'Enviar respuesta' : 'Enviar comentario'}
            </Button>
            {drafting && <Button size="sm" variant="ghost" disabled={busy} onClick={discardDraft}>Descartar borrador</Button>}
          </div>
        </form>
      )}
    </div>
  )
}

function ApplicationDiscussions({ applicationId, onDirty }: { applicationId: string; onDirty: (dirty: boolean) => void }) {
  const [offset, setOffset] = useState(0)
  const [selection, setSelection] = useState('')
  const [subject, setSubject] = useState('')
  const [newThread, setNewThread] = useState<Thread | null>(null)
  const [commentDirty, setCommentDirty] = useState(false)
  const threadSelectId = useId()
  const subjectId = useId()
  const { save, busy, error } = useDiscussionWrite()
  useEffect(() => {
    onDirty(Boolean(subject.trim()) || commentDirty || busy)
  }, [subject, commentDirty, busy, onDirty])
  const read = useCallback((signal: AbortSignal) => api.GET('/api/v1/discussion-threads', {
    params: { query: { scope_type: 'application', application_id: applicationId, limit: PAGE_SIZE, offset } },
    signal,
  }), [applicationId, offset])
  const { state, refresh } = useDiscussionRead(read)
  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!subject.trim() || commentDirty) return
    const thread = await save(() => api.POST('/api/v1/discussion-threads', {
      body: { scope_type: 'application', application_id: applicationId, subject: subject.trim() },
    }))
    if (!thread) return
    setSubject('')
    setSelection(thread.id)
    setNewThread(thread)
    if (state && 'data' in state) setOffset(Math.floor(state.data.total / PAGE_SIZE) * PAGE_SIZE)
    refresh()
  }

  if (!state) return <p role="status" className="text-sm text-muted">Cargando hilos…</p>
  if ('error' in state) return <DiscussionReadError message={state.error} retry={refresh} />
  const { items, total } = state.data
  const options = newThread && !items.some(item => item.id === newThread.id) ? [...items, newThread] : items
  const thread = options.find(item => item.id === selection) ?? options[0]
  return (
    <div className="space-y-3">
      <form className="grid justify-items-start gap-2" onSubmit={create}>
        <div className="w-full">
          <Field label="Asunto del nuevo hilo" htmlFor={subjectId}>
            <input id={subjectId} className={inputCls} maxLength={160} value={subject} disabled={busy}
              onChange={event => setSubject(event.target.value)} />
          </Field>
        </div>
        {error && <Notice tone="warning" live="polite">{error.message}</Notice>}
        <Button size="sm" type="submit" disabled={busy || commentDirty || !subject.trim()}>Crear hilo</Button>
        <Button size="sm" variant="ghost" disabled={busy || commentDirty} onClick={refresh}>Actualizar hilos</Button>
      </form>
      {thread ? (
        <>
          <Field label="Hilo" htmlFor={threadSelectId}>
            <select id={threadSelectId} value={thread.id} className={inputCls} disabled={commentDirty || busy}
              onChange={event => setSelection(event.target.value)}>
              {options.map(item => <option key={item.id} value={item.id}>{item.subject}</option>)}
            </select>
          </Field>
          {!commentDirty && !busy && <PageControls label="Páginas de hilos" offset={offset} total={total} onPage={next => {
            setOffset(next)
            setNewThread(null)
            setSelection('')
          }} />}
          <ThreadComments key={thread.id} threadId={thread.id} onDirty={setCommentDirty} />
        </>
      ) : <Empty>Este expediente todavía no tiene hilos.</Empty>}
    </div>
  )
}

export function ServerDiscussions({ applicationId, onDirty }: { applicationId: string; onDirty: (dirty: boolean) => void }) {
  const [opened, setOpened] = useState(false)
  return (
    <details className="rounded-xl border border-line p-3" onToggle={event => {
      if (event.currentTarget.open) setOpened(true)
    }}>
      <summary className="cursor-pointer font-semibold">Comentarios internos</summary>
      {opened && <div className="mt-3"><ApplicationDiscussions applicationId={applicationId} onDirty={onDirty} /></div>}
    </details>
  )
}
