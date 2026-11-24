import { describe, expect, it, vi } from 'vitest'
import { createPublicCatalogClient, PublicCatalogError } from '../publicCatalog'

describe('public catalogue transport', () => {
  it('uses generated list filters and never attaches credentials', async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(new Response(JSON.stringify({ items: [], total: 0 })))
    const client = createPublicCatalogClient('https://synthetic.example', fetcher)
    expect(await client.list({ programId: 'P-IA', admissionState: 'abierta', offset: 20 })).toEqual({ items: [], total: 0 })
    const request = fetcher.mock.calls[0][0] as Request
    const url = new URL(request.url)
    expect(url.pathname).toBe('/api/v1/public/courses')
    expect(Object.fromEntries(url.searchParams)).toEqual({ program_id: 'P-IA', admission_state: 'abierta', limit: '20', offset: '20' })
    expect(request.credentials).toBe('omit')
    expect(request.headers.has('Authorization')).toBe(false)
  })

  it('encodes an offer identifier as a path parameter', async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(new Response('{}'))
    await createPublicCatalogClient('https://synthetic.example', fetcher).get('offer/with space')
    expect((fetcher.mock.calls[0][0] as Request).url).toContain('offer%2Fwith%20space')
  })

  it.each([404, 403, 422, 500])('shows a safe message for %i without rendering backend details', async (status) => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(new Response('{"detail":"INTERNAL-CANARY"}', { status }))
    const promise = createPublicCatalogClient('https://synthetic.example', fetcher).get('UNKNOWN')
    await expect(promise).rejects.toBeInstanceOf(PublicCatalogError)
    await expect(promise).rejects.not.toThrow('INTERNAL-CANARY')
  })

  it('turns connectivity failures into an actionable message', async () => {
    const client = createPublicCatalogClient('https://synthetic.example', vi.fn<typeof fetch>().mockRejectedValue(new TypeError('network')))
    await expect(client.list()).rejects.toThrow('Comprueba tu conexión')
  })

  it('preserves cancellation so obsolete requests can be ignored', async () => {
    const controller = new AbortController()
    controller.abort()
    const abort = new DOMException('Aborted', 'AbortError')
    const client = createPublicCatalogClient('https://synthetic.example', vi.fn<typeof fetch>().mockRejectedValue(abort))
    await expect(client.list({}, controller.signal)).rejects.toBe(abort)
  })
})
