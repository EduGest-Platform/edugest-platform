import { describe, expect, it } from 'vitest'
import { API_VIEWS, dataSourceFor } from '../../shared/api/config'
import { API_SCREENS } from '../apiScreens'
import { VIEWS } from '../config'

const ALL_VIEWS = Object.keys(VIEWS)

describe('dataSourceFor (KAN-89)', () => {
  it('keeps every view local when there is no API URL', () => {
    for (const view of ALL_VIEWS) expect(dataSourceFor(view, false)).toBe('local')
  })

  it('uses the API only for migrated views in API mode', () => {
    const apiViews = ALL_VIEWS.filter((view) => ['coder', 'coordinacion'].some((role) => dataSourceFor(view, true, role) === 'api'))
    expect(apiViews.sort()).toEqual([...API_VIEWS].sort())
  })

  it('opens server deliveries for coders while preserving the teacher demo view', () => {
    expect(dataSourceFor('entregas', true, 'coder')).toBe('api')
    expect(dataSourceFor('entregas', true, 'docente')).toBe('local')
    expect(dataSourceFor('entregas', false, 'coder')).toBe('local')
    expect(dataSourceFor('entregas', true)).toBe('local')
  })

  it('opens the API dashboard for coordination and keeps other home views local', () => {
    expect(dataSourceFor('dashboard', true, 'coordinacion')).toBe('api')
    expect(dataSourceFor('dashboard', false, 'coordinacion')).toBe('local')
    expect(dataSourceFor('dashboard', true, 'docente')).toBe('local')
  })

  it('treats unknown views as local, never as API', () => {
    expect(dataSourceFor('vista-inexistente', true)).toBe('local')
  })
})

describe('API view registry', () => {
  it('lists only views that exist in the menu configuration', () => {
    for (const view of API_VIEWS) expect(ALL_VIEWS).toContain(view)
  })

  it('has an API screen for every migrated view and none for local views', () => {
    expect(Object.keys(API_SCREENS).sort()).toEqual([...API_VIEWS].sort())
  })
})
