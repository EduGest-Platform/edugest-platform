import { PublicCatalogError } from '../../../shared/api/publicCatalog'
import type { PublicResource } from './PublicCourseList'

/** One subscription owns one request; cancellation prevents every later publication. */
export function observePublicRead<T>(read: (signal: AbortSignal) => Promise<T>, publish: (state: PublicResource<T>) => void) {
  const controller = new AbortController()
  publish({ status: 'loading' })
  void Promise.resolve().then(() => read(controller.signal)).then((data) => {
    if (!controller.signal.aborted) publish({ status: 'ready', data })
  }).catch((error: unknown) => {
    if (!controller.signal.aborted) publish({ status: 'error', message: error instanceof PublicCatalogError
      ? error.message : 'No se pudieron cargar las formaciones. Vuelve a intentarlo.' })
  })
  return () => controller.abort()
}
