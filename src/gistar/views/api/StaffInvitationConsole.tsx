import { useEffect, useRef, useState, type FormEvent } from 'react'
import { api, type Schemas } from '../../../shared/api/client'
import { describeApiError, problemText } from '../../../shared/api/errors'
import { Button, Field, Notice, inputCls } from '../../ui'

type Account = Schemas['InvitationAccount']
type Directory = Schemas['InvitationDirectory']
type Action = 'issue' | 'renew' | 'revoke'
const pageSize = 12
const formatDate = new Intl.DateTimeFormat('es-ES', { dateStyle: 'medium', timeStyle: 'short' })

function invitationState(account: Account) {
  const invitation = account.latest_invitation
  if (account.profile_state === 'active') return 'Ficha activa'
  if (!invitation) return 'Sin invitación'
  if (invitation.used_at) return 'Utilizada'
  if (invitation.revoked_at) return 'Revocada'
  return Date.parse(invitation.expires_at) <= Date.now() ? 'Caducada' : 'Pendiente de aceptación'
}

export function StaffInvitationConsole({ onBlockedChange }: { onBlockedChange: (blocked: boolean) => void }) {
  const [opened, setOpened] = useState(false)
  const [directory, setDirectory] = useState<Directory>()
  const [search, setSearch] = useState({ term: '', offset: 0 })
  const [input, setInput] = useState('')
  const [selection, setSelection] = useState('')
  const [attempt, setAttempt] = useState(0)
  const [hours, setHours] = useState('24')
  const [receipt, setReceipt] = useState<{ token: string; displayName: string; expiresAt: string }>()
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [uncertain, setUncertain] = useState(false)
  const writing = useRef<AbortController | null>(null)
  const account = directory?.items.find(item => item.user_id === selection)

  const blocked = busy || uncertain
  useEffect(() => { onBlockedChange(blocked) }, [blocked, onBlockedChange])
  useEffect(() => () => {
    writing.current?.abort()
    onBlockedChange(false)
  }, [onBlockedChange])
  useEffect(() => {
    if (!opened) return
    const controller = new AbortController()
    setDirectory(undefined)
    void api.GET('/api/v1/staff/invitation-accounts', {
      params: { query: { search: search.term, offset: search.offset, limit: pageSize } }, signal: controller.signal,
    }).then(result => {
      if (controller.signal.aborted) return
      if (result.data) setDirectory(result.data)
      else setError(problemText(describeApiError(result.response.status, result.error)))
    }).catch(() => {
      if (!controller.signal.aborted) setError('No se pudieron cargar las cuentas internas.')
    })
    return () => controller.abort()
  }, [opened, search, attempt])

  function page(term: string, offset: number) {
    setSelection('')
    setReceipt(undefined)
    setError('')
    setNotice('')
    setSearch({ term, offset })
  }

  async function change(action: Action) {
    if (!account || writing.current || uncertain || account.profile_state === 'active') return
    const expiresHours = Number(hours)
    if (action !== 'revoke' && (!Number.isInteger(expiresHours) || expiresHours < 1 || expiresHours > 168)) {
      setError('Indica entre 1 y 168 horas de vigencia.')
      return
    }
    const invitation = account.latest_invitation
    if (action !== 'issue' && !invitation) return
    if (action === 'revoke' && !window.confirm(`¿Revocar la invitación de ${account.display_name}?`)) return
    const controller = new AbortController()
    writing.current = controller
    setBusy(true)
    setReceipt(undefined)
    setError('')
    setNotice('')
    try {
      const signal = controller.signal
      if (action === 'revoke' && invitation) {
        const result = await api.POST('/api/v1/staff/invitations/{invitation_id}/revoke', {
          params: { path: { invitation_id: invitation.id } }, signal,
        })
        if (signal.aborted) return
        if (result.data) setNotice('Invitación revocada.')
        else {
          if (result.response.status >= 500 || result.response.status === 408 || result.response.status === 409) setUncertain(true)
          setError(problemText(describeApiError(result.response.status, result.error)))
        }
      } else {
        const result = action === 'renew' && invitation
          ? await api.POST('/api/v1/staff/invitations/{invitation_id}/renew', {
            params: { path: { invitation_id: invitation.id } }, body: { expires_hours: expiresHours }, signal,
          })
          : await api.POST('/api/v1/staff/invitations', { body: { user_id: account.user_id, expires_hours: expiresHours }, signal })
        if (signal.aborted) return
        if (result.data) setReceipt({
          token: result.data.token,
          displayName: account.display_name,
          expiresAt: result.data.invitation.expires_at,
        })
        else {
          if (result.response.status >= 500 || result.response.status === 408 || result.response.status === 409) setUncertain(true)
          setError(problemText(describeApiError(result.response.status, result.error)))
        }
      }
      setDirectory(undefined)
      setAttempt(value => value + 1)
    } catch {
      if (!controller.signal.aborted) {
        setUncertain(true)
        setError('No se pudo confirmar la operación. Comprueba el estado actualizado antes de emitir otro código.')
        setDirectory(undefined)
        setAttempt(value => value + 1)
      }
    } finally {
      writing.current = null
      if (!controller.signal.aborted) setBusy(false)
    }
  }

  function toggle() {
    if (blocked) return
    setReceipt(undefined)
    setError('')
    setNotice('')
    setOpened(value => !value)
  }

  return (
    <section className="grid gap-3 rounded-xl border border-line p-3" aria-label="Invitaciones de personal">
      <Button variant="ghost" className="justify-self-start" size="sm" onClick={toggle} aria-expanded={opened}
        disabled={blocked}>{opened ? 'Cerrar gestión de invitaciones' : 'Gestionar invitaciones'}</Button>
      {opened && <>
        <form className="flex flex-wrap items-end gap-2" onSubmit={(event: FormEvent) => {
          event.preventDefault()
          if (!blocked) page(input.trim(), 0)
        }}>
          <Field label="Buscar cuenta interna por nombre" htmlFor="staff-invitation-search">
            <input id="staff-invitation-search" className={inputCls} value={input} maxLength={100}
              onChange={event => setInput(event.target.value)} disabled={blocked} />
          </Field>
          <Button size="sm" type="submit" disabled={blocked}>Buscar cuenta</Button>
        </form>
        {error && <Notice tone="warning" live="assertive">{error}</Notice>}
        {notice && <Notice live="polite">{notice}</Notice>}
        {busy && <p role="status">Actualizando invitación…</p>}
        {uncertain && <Notice tone="warning">
          El servidor puede haber aplicado la operación. Comprueba el estado de esta cuenta.
          Si se emitió un código que no recibiste, puedes recuperarte renovándolo. La renovación invalida el anterior.
        </Notice>}
        {uncertain && !directory && error && <Button size="sm" variant="ghost" onClick={() => {
          setError('')
          setAttempt(value => value + 1)
        }}>Actualizar estado de la invitación</Button>}
        {uncertain && directory && <Button size="sm" variant="ghost" disabled={busy} onClick={() => {
          setUncertain(false)
          setError('')
        }}>He revisado el estado de las invitaciones</Button>}
        {!directory && !error && <p role="status">Cargando cuentas internas…</p>}
        {directory && <>
          {directory.items.length === 0 ? <p>No hay cuentas en esta página.</p> : (
            <Field label="Cuenta interna" htmlFor="staff-invitation-account">
              <select id="staff-invitation-account" className={inputCls} value={selection} disabled={blocked}
                onChange={event => { setSelection(event.target.value); setReceipt(undefined); setError(''); setNotice('') }}>
                <option value="">Elige una cuenta</option>
                {directory.items.map(item => <option key={item.user_id} value={item.user_id}>
                  {item.display_name} · {invitationState(item)} · {item.user_id.slice(0, 8)}
                </option>)}
              </select>
            </Field>
          )}
          {(search.offset > 0 || directory.has_more) && <nav className="flex gap-2" aria-label="Páginas de cuentas internas">
            <Button size="sm" variant="ghost" disabled={blocked || search.offset === 0}
              onClick={() => page(search.term, search.offset - pageSize)}>Anterior</Button>
            <Button size="sm" variant="ghost" disabled={blocked || !directory.has_more}
              onClick={() => page(search.term, search.offset + pageSize)}>Siguiente</Button>
          </nav>}
        </>}
        {account && <div className="grid gap-2">
          <p>{invitationState(account)}{account.latest_invitation && ` · Vence ${formatDate.format(new Date(account.latest_invitation.expires_at))}`}</p>
          {account.profile_state !== 'active' && <>
            <Field label="Vigencia en horas" htmlFor="staff-invitation-hours">
              <input id="staff-invitation-hours" className={inputCls} type="number" min={1} max={168} value={hours}
                onChange={event => setHours(event.target.value)} disabled={blocked} />
            </Field>
            <div className="flex flex-wrap gap-2">
              <Button size="sm" disabled={busy || uncertain} onClick={() => void change(account.latest_invitation ? 'renew' : 'issue')}>
                {account.latest_invitation ? 'Renovar código' : 'Emitir código'}
              </Button>
              {account.latest_invitation && !account.latest_invitation.revoked_at && !account.latest_invitation.used_at &&
                <Button size="sm" variant="ghost" disabled={blocked} onClick={() => void change('revoke')}>Revocar código</Button>}
            </div>
          </>}
        </div>}
        {receipt && <div className="grid gap-2 rounded-lg bg-mist p-3">
          <p role="status">Código para {receipt.displayName} · Vence {formatDate.format(new Date(receipt.expiresAt))}</p>
          <p className="text-sm">Este código solo se muestra al emitirlo. Entrégalo a la persona titular por un canal autorizado.</p>
          <code className="break-all select-all">{receipt.token}</code>
          <Button size="sm" variant="ghost" className="justify-self-start" onClick={() => setReceipt(undefined)}>Ocultar código</Button>
        </div>}
      </>}
    </section>
  )
}
