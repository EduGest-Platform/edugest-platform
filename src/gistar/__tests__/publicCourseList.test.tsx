import { describe, expect, it } from 'vitest'
import { renderToStaticMarkup } from 'react-dom/server'
import { PublicCourseList, courseDate } from '../views/api/PublicCourseList'
import type { PublicCourse } from '../../shared/api/publicCatalog'

export const syntheticCourse: PublicCourse = {
  id: 'SYNTHETIC-COURSE', program_id: 'SYNTHETIC-PROGRAM', program_name: 'Programa sintético',
  name: 'Formación sintética', opens_on: '2030-03-31', closes_on: '2030-10-27',
  capacity: 20, admission_state: 'abierta',
}
const actions = { onFilter() {}, onPage() {}, onOpen() {}, onRetry() {} }

describe('public course list', () => {
  it('announces loading without showing stale offers or controls', () => {
    const html = renderToStaticMarkup(<PublicCourseList {...actions} admission="" offset={0} state={{ status: 'loading' }} />)
    expect(html).toContain('role="status"')
    expect(html).toContain('Cargando formaciones')
    expect(html).not.toContain('Ver formación')
  })

  it('offers a retry after error and explains empty results separately', () => {
    const error = renderToStaticMarkup(<PublicCourseList {...actions} admission="" offset={0} state={{ status: 'error', message: 'Comprueba tu conexión.' }} />)
    expect(error).toContain('Volver a cargar formaciones')
    expect(error).not.toContain('No hay formaciones')
    const empty = renderToStaticMarkup(<PublicCourseList {...actions} admission="" offset={0} state={{ status: 'ready', data: { items: [], total: 0 } }} />)
    expect(empty).toContain('No hay formaciones')
    expect(empty.match(/disabled=""/g)).toHaveLength(2)
  })

  it('renders offer names as text with labelled controls and calendar dates', () => {
    const html = renderToStaticMarkup(<PublicCourseList {...actions} admission="" offset={0} state={{ status: 'ready', data: { items: [{ ...syntheticCourse, name: '<img src=x onerror=alert(1)>' }], total: 21 } }} />)
    expect(html).toContain('&lt;img')
    expect(html).not.toContain('<img')
    expect(html).toContain('for="public-admission-filter"')
    expect(html).toContain('dateTime="2030-03-31"')
    expect(html.match(/disabled=""/g)).toHaveLength(1)
    expect(html).not.toContain('Solicitar plaza')
  })

  it('preserves the day across daylight-saving boundaries', () => {
    expect(courseDate('2030-03-31')).toContain('31')
    expect(courseDate('2030-10-27')).toContain('27')
  })
})
