import type { PublicAccessView } from './PublicAccessNavigation'

export type PublicAccessLocation = { view: PublicAccessView; callId?: string }

export function readPublicAccess(search: string): PublicAccessLocation {
  const params = new URLSearchParams(search)
  switch (params.get('vista')) {
    case 'catalogo':
      return { view: 'catalogo' }
    case 'inscripcion':
      return { view: 'inscripcion', callId: params.get('convocatoria') || undefined }
    default:
      return { view: 'login' }
  }
}

export function publicAccessUrl(currentUrl: string, { view, callId }: PublicAccessLocation): URL {
  const url = new URL(currentUrl)
  if (view === 'login') url.searchParams.delete('vista')
  else url.searchParams.set('vista', view)
  if (view === 'inscripcion' && callId) url.searchParams.set('convocatoria', callId)
  else url.searchParams.delete('convocatoria')
  return url
}
