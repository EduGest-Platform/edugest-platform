import { afterEach, describe, expect, it, vi } from 'vitest'
import { renderToStaticMarkup } from 'react-dom/server'
import { Modal } from '../components/Modal'

vi.mock('react-dom', () => ({ createPortal: (children: unknown) => children }))
afterEach(() => vi.unstubAllGlobals())

describe('dialog placement', () => {
  it('preserves dialog semantics in a side panel', () => {
    vi.stubGlobal('document', { body: {} })
    const html = renderToStaticMarkup(<Modal open placement="end" title="Detalle" onClose={() => {}}>Contenido</Modal>)
    expect(html).toContain('role="dialog"')
    expect(html).toContain('aria-modal="true"')
    expect(html).toContain('justify-end')
    expect(html).toContain('motion-safe:animate-')
  })
})
