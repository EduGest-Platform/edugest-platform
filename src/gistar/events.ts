import type { CalItem, EventType } from './types'

const normalizeSearch = (value: string) => value.toLocaleLowerCase('es').normalize('NFD').replace(/\p{Diacritic}/gu, '')

export function filterEvents(items: CalItem[], now: string, query: string, type: EventType | '', upcoming: boolean): CalItem[] {
  const needle = normalizeSearch(query.trim())
  return items
    .filter(item => item.tipo !== 'entrega' && item.estado !== 'cancelado')
    .filter(item => !upcoming || item.fin >= now)
    .filter(item => !type || item.tipo === type)
    .filter(item => normalizeSearch(item.titulo).includes(needle))
    .sort((a, b) => a.inicio.localeCompare(b.inicio) || a.id.localeCompare(b.id))
}

export function eventPhase(item: Pick<CalItem, 'inicio' | 'fin'>, now: string): 'upcoming' | 'ongoing' | 'ended' {
  if (item.fin < now) return 'ended'
  return item.inicio > now ? 'upcoming' : 'ongoing'
}
