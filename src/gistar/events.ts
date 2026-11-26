import type { CalItem, EventType } from './types'

export function filterEvents(items: CalItem[], now: string, query: string, type: EventType | '', upcoming: boolean): CalItem[] {
  const needle = query.trim().toLocaleLowerCase('es')
  return items
    .filter(item => item.tipo !== 'entrega' && item.estado !== 'cancelado')
    .filter(item => !upcoming || item.fin >= now)
    .filter(item => !type || item.tipo === type)
    .filter(item => item.titulo.toLocaleLowerCase('es').includes(needle))
    .sort((a, b) => a.inicio.localeCompare(b.inicio) || a.id.localeCompare(b.id))
}
