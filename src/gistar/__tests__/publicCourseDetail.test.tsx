import { describe, expect, it, vi } from 'vitest'
import { renderToStaticMarkup } from 'react-dom/server'
import { PublicCourseDetail } from '../views/api/PublicCourseDetail'
import { observePublicRead } from '../views/api/publicCatalogResource'
import { PublicCatalogError, type PublicCourse } from '../../shared/api/publicCatalog'

const course: PublicCourse = { id: 'SYNTHETIC', name: 'Formación sintética', program_id: 'P-SYNTHETIC',
  program_name: 'Programa sintético', opens_on: '2030-01-01', closes_on: '2030-02-01', capacity: 0, admission_state: 'abierta' }
const actions = { onBack() {}, onRetry() {}, onApply() {} }

describe('public course detail', () => {
  it('offers a human application only for open offers without inventing vacancies', () => {
    const html = renderToStaticMarkup(<PublicCourseDetail {...actions} state={{ status: 'ready', data: course }} />)
    expect(html).toContain('Solicitar plaza')
    expect(html).toContain('Plazas ofertadas')
    expect(html).toContain('no garantiza una plaza')
    expect(html).not.toContain('plazas disponibles')
    const closed = renderToStaticMarkup(<PublicCourseDetail {...actions} state={{ status: 'ready', data: { ...course, admission_state: 'cerrada' } }} />)
    expect(closed).not.toContain('Solicitar plaza')
    expect(closed).toContain('Inscripción cerrada')
  })

  it('never exposes a stale apply action while loading or unavailable', () => {
    for (const state of [{ status: 'loading' } as const, { status: 'error', message: new PublicCatalogError(404).message } as const]) {
      const html = renderToStaticMarkup(<PublicCourseDetail {...actions} state={state} />)
      expect(html).not.toContain('Solicitar plaza')
      expect(html).toContain('Volver al catálogo')
    }
  })

  it('ignores a late success after a cancelled subscription', async () => {
    let resolve!: (value: string) => void
    const result = new Promise<string>((done) => { resolve = done })
    const publish = vi.fn()
    const stop = observePublicRead(() => result, publish)
    stop()
    resolve('STALE-OFFER')
    await vi.waitFor(() => expect(publish).toHaveBeenCalledTimes(1))
    await new Promise((done) => setTimeout(done, 0))
    expect(publish).toHaveBeenCalledExactlyOnceWith({ status: 'loading' })
  })

  it('publishes an actionable not-found message without private error data', async () => {
    const publish = vi.fn()
    observePublicRead(() => Promise.reject(new PublicCatalogError(404)), publish)
    await vi.waitFor(() => expect(publish).toHaveBeenLastCalledWith({ status: 'error', message: expect.stringContaining('Vuelve al catálogo') }))
  })

  it('ignores a late failure after navigation and hides unexpected diagnostic messages', async () => {
    let reject!: (error: Error) => void
    const pending = new Promise<string>((_, fail) => { reject = fail })
    const oldPublish = vi.fn()
    const stop = observePublicRead(() => pending, oldPublish)
    stop()
    reject(new Error('INTERNAL-CANARY'))
    await new Promise((done) => setTimeout(done, 0))
    expect(oldPublish).toHaveBeenCalledExactlyOnceWith({ status: 'loading' })
    const publish = vi.fn()
    observePublicRead(() => Promise.reject(new Error('INTERNAL-CANARY')), publish)
    await vi.waitFor(() => expect(publish).toHaveBeenLastCalledWith({ status: 'error', message: 'No se pudieron cargar las formaciones. Vuelve a intentarlo.' }))
  })
})
