import createClient from 'openapi-fetch'
import type { components, paths } from './schema.gen'
import { API_URL } from './config'
import { describeApiError, problemText } from './errors'

export type PublicCourse = components['schemas']['PublicCourseOut']
export type PublicCoursePage = components['schemas']['PublicCourseList']
export interface CourseFilters {
  programId?: string
  admissionState?: 'abierta' | 'cerrada'
  offset?: number
  limit?: number
}

export class PublicCatalogError extends Error {
  constructor(readonly status?: number) {
    super(status === 404
      ? 'Esta formación ya no está disponible. Vuelve al catálogo para consultar otras ofertas.'
      : problemText(describeApiError(status)))
    this.name = 'PublicCatalogError'
  }
}

/** Separate public transport: never attach session tokens or send cookies. */
export function createPublicCatalogClient(baseUrl: string, fetcher: typeof fetch = globalThis.fetch) {
  const client = createClient<paths>({ baseUrl, fetch: fetcher, credentials: 'omit' })
  async function read<T>(request: () => Promise<{ data?: T; response: Response }>, signal?: AbortSignal): Promise<T> {
    try {
      const { data, response } = await request()
      if (!response.ok || !data) throw new PublicCatalogError(response.status)
      return data
    } catch (error) {
      if (signal?.aborted || error instanceof PublicCatalogError) throw error
      throw new PublicCatalogError()
    }
  }
  return {
    list(filters: CourseFilters = {}, signal?: AbortSignal) {
      return read<PublicCoursePage>(() => client.GET('/api/v1/public/courses', {
        signal,
        params: { query: {
          program_id: filters.programId || undefined, admission_state: filters.admissionState,
          limit: filters.limit ?? 20, offset: filters.offset ?? 0,
        } },
      }), signal)
    },
    get(id: string, signal?: AbortSignal) {
      return read<PublicCourse>(() => client.GET('/api/v1/public/courses/{course_id}', {
        signal, params: { path: { course_id: id } },
      }), signal)
    },
  }
}

export const publicCatalog = createPublicCatalogClient(API_URL ?? '')
