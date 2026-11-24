import { afterEach, describe, expect, it, vi } from 'vitest'
import { renderToStaticMarkup } from 'react-dom/server'
import { Modal } from '../components/Modal'
import { Button } from '../ui'

vi.mock('react-dom', () => ({ createPortal: (children: unknown) => children }))
afterEach(() => vi.unstubAllGlobals())

describe('protected modal footer closure', () => {
  function render(dirty: boolean) {
    vi.stubGlobal('document', { body: {} })
    const onClose = vi.fn()
    let closeFromFooter: () => void = () => { throw new Error('Footer not rendered') }
    const reason = 'Motivo sintético sin enviar'
    const html = renderToStaticMarkup(<Modal open dirty={dirty} title="Expediente" onClose={onClose} footer={requestClose => {
      closeFromFooter = requestClose
      return <Button onClick={requestClose}>Cerrar</Button>
    }}><textarea defaultValue={reason} /></Modal>)
    return { onClose, closeFromFooter, reason, html }
  }
  it('cancel keeps the unsent reason and never invokes the destructive close', () => {
    const confirm = vi.fn(() => false)
    vi.stubGlobal('confirm', confirm)
    const modal = render(true)
    modal.closeFromFooter()
    expect(confirm).toHaveBeenCalledOnce()
    expect(modal.onClose).not.toHaveBeenCalled()
    expect(modal.html).toContain(modal.reason)
    // The same still-open dialog can be closed only after explicit acceptance.
    confirm.mockReturnValue(true)
    modal.closeFromFooter()
    expect(modal.onClose).toHaveBeenCalledOnce()
  })
  it('clean closure does not ask to discard anything', () => {
    const confirm = vi.fn(() => false)
    vi.stubGlobal('confirm', confirm)
    const modal = render(false)
    modal.closeFromFooter()
    expect(confirm).not.toHaveBeenCalled()
    expect(modal.onClose).toHaveBeenCalledOnce()
  })
})
