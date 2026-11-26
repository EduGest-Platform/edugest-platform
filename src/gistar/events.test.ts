import { describe, expect, it } from 'vitest'
import { canOpen, MENUS } from './config'
import { filterEvents } from './events'
import type { CalItem, Role } from './types'

const now = '2026-11-26T10:00'
const event = (id: string, overrides: Partial<CalItem> = {}): CalItem => ({
  id, titulo: 'Taller de IA', tipo: 'taller', estado: 'programado',
  inicio: '2026-11-26T11:00', fin: '2026-11-26T12:00',
  ...overrides,
} as CalItem)

describe('Eventos', () => {
  it('is reachable for every role in both modes', () => {
    for (const role of Object.keys(MENUS) as Role[]) {
      expect(canOpen(role, 'eventos')).toBe(true)
      expect(canOpen(role, 'eventos', true)).toBe(true)
    }
  })
  it('excludes cancelled events and deliveries even without upcoming filter', () => {
    expect(filterEvents([event('ok'), event('cancel', { estado: 'cancelado' }), event('task', { tipo: 'entrega' })], now, '', '', false).map(x => x.id)).toEqual(['ok'])
  })
  it('includes ongoing events and excludes ended events by default', () => {
    const items = [event('past', { inicio: '2026-11-26T08:00', fin: '2026-11-26T09:00' }), event('ongoing', { inicio: '2026-11-26T09:00' })]
    expect(filterEvents(items, now, '', '', true).map(x => x.id)).toEqual(['ongoing'])
    expect(filterEvents(items, now, '', '', false)).toHaveLength(2)
  })
  it('combines title and type filters and sorts without mutating input', () => {
    const items = [event('b'), event('a'), event('other', { titulo: 'Otra actividad' })]
    expect(filterEvents(items, now, '  TALLER ', 'taller', true).map(x => x.id)).toEqual(['a', 'b'])
    expect(items.map(x => x.id)).toEqual(['b', 'a', 'other'])
    expect(filterEvents(items, now, 'missing', '', true)).toEqual([])
  })
})
