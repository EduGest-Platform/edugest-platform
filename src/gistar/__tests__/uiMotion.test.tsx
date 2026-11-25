import { describe, expect, it } from 'vitest'
import { renderToStaticMarkup } from 'react-dom/server'
import { Button, Progress } from '../ui'

describe('accessible motion', () => {
  it('gates button feedback and progress transitions on motion preference', () => {
    expect(renderToStaticMarkup(<Button>Guardar</Button>)).toContain('motion-safe:active:scale')
    expect(renderToStaticMarkup(<Progress value={40} />)).toContain('motion-safe:transition-[width]')
  })
})
