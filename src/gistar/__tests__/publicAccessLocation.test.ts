import { describe, expect, it } from 'vitest'
import { publicAccessUrl, readPublicAccess } from '../components/publicAccessLocation'

describe('public access location', () => {
  it('restores a selected call from the address and clears it on other views', () => {
    const form = publicAccessUrl('http://localhost/?demo=1', { view: 'inscripcion', callId: 'CONV-IA-2027A' })
    expect(readPublicAccess(form.search)).toEqual({ view: 'inscripcion', callId: 'CONV-IA-2027A' })
    const catalog = publicAccessUrl(form.href, { view: 'catalogo' })
    expect(readPublicAccess(catalog.search)).toEqual({ view: 'catalogo' })
    expect(catalog.searchParams.get('convocatoria')).toBeNull()
    expect(catalog.searchParams.get('demo')).toBe('1')
  })

  it('restores the login for an unknown view and ignores a stray call', () => {
    expect(readPublicAccess('?vista=unknown&convocatoria=example')).toEqual({ view: 'login' })
    expect(readPublicAccess(publicAccessUrl('http://localhost/?vista=inscripcion', { view: 'login' }).search))
      .toEqual({ view: 'login' })
  })
})
