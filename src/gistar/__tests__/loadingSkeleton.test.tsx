import { describe, expect, it } from 'vitest'
import { renderToStaticMarkup } from 'react-dom/server'
import { LoadingSkeleton } from '../components/LoadingSkeleton'

describe('loading skeleton', () => {
  it('announces loading and hides decorative placeholders', () => {
    const html = renderToStaticMarkup(<LoadingSkeleton label="Cargando progreso…" rows={2} />)
    expect(html).toContain('role="status"')
    expect(html).toContain('Cargando progreso…')
    expect(html).toContain('aria-hidden="true"')
    expect(html).toContain('motion-safe:animate-pulse')
    expect(html.match(/h-3 w-2\/5/g)).toHaveLength(2)
  })
})
