import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import type { Schemas } from '../../shared/api/client'
import { OverviewAttendanceCard } from '../views/api/OverviewAttendanceCard'
import { OverviewCompetenciesCard } from '../views/api/OverviewCompetenciesCard'
import { OverviewDeliveriesCard } from '../views/api/OverviewDeliveriesCard'

const attendance: Schemas['OverviewAttendance'] = {
  date_from: null, date_to: null, has_data: true, rule: 'Día completo = 1, media jornada = 0,5.',
  totals: {
    enrollments: 5, suppressed: false, min_group_size: 5,
    attended_days: 0.5, justified_absence_days: 0, unjustified_absence_days: 0.5,
    unrecorded_days: 1, attendance_rate: 0.5,
  },
}

const submissions: Schemas['OverviewSubmissions'] = {
  as_of: '2026-11-25T10:00:00Z', period: 'current_published_assignments',
  rule: 'Regla de entregas.', has_data: true, suppressed: false, min_group_size: 5,
  assignments: [{
    assignment_id: 'synthetic-project', title: 'Proyecto sintético',
    due_at: '2026-11-30T18:00:00Z', counts: { on_time: 2, late: 0, pending: 3, overdue: 0, reviewed: 1 },
  }],
}

const competencies: Schemas['OverviewCompetencies'] = {
  period: 'current_assigned_framework', rule: 'Última evaluación.', framework_version: 2,
  has_data: true, suppressed: false, min_group_size: 5,
  distribution: [{ codigo: 'C1', nombre: 'Competencia sintética', counts: { level_1: 0, level_2: 2, level_3: 1, not_assessed: 2 } }],
}

describe('server cohort analytics cards', () => {
  it('renders half-day attendance, a genuine zero and an unrecorded day', () => {
    const html = renderToStaticMarkup(<OverviewAttendanceCard attendance={attendance} />)
    expect(html).toContain('>0,5<')
    expect(html).toContain('>0<')
    expect(html).toContain('Días sin registrar')
    expect(html).toContain('Tasa sobre días registrados')
  })

  it('does not render counts or charts for suppressed groups', () => {
    const html = renderToStaticMarkup(
      <>
        <OverviewAttendanceCard attendance={{ ...attendance, has_data: null, totals: { ...attendance.totals, suppressed: true } }} />
        <OverviewDeliveriesCard submissions={{ ...submissions, has_data: null, suppressed: true }} timezone="Europe/Madrid" />
        <OverviewCompetenciesCard competencies={{ ...competencies, has_data: null, suppressed: true }} />
      </>,
    )
    expect(html.match(/por el tamaño del grupo/g)).toHaveLength(3)
    expect(html).not.toContain('Días asistidos')
    expect(html).not.toContain('Proyecto sintético')
    expect(html).not.toContain('Competencia sintética')
    expect(html).not.toContain('role="img"')
  })

  it('distinguishes pending work, an unassessed competency and unavailable data', () => {
    const deliveries = renderToStaticMarkup(<OverviewDeliveriesCard submissions={submissions} timezone="Europe/Madrid" />)
    expect(deliveries).toContain('Pendientes')
    expect(deliveries).toContain('<td>3</td>')
    const levels = renderToStaticMarkup(<OverviewCompetenciesCard competencies={competencies} />)
    expect(levels).toContain('Nivel 1: 0 de 5, Nivel 2: 2 de 5, Nivel 3: 1 de 5, Sin evaluar: 2 de 5')

    const empty = renderToStaticMarkup(
      <>
        <OverviewAttendanceCard attendance={{ ...attendance, has_data: false }} />
        <OverviewDeliveriesCard submissions={{ ...submissions, has_data: false, assignments: [] }} timezone="Europe/Madrid" />
        <OverviewCompetenciesCard competencies={{ ...competencies, has_data: false }} />
      </>,
    )
    expect(empty).toContain('No hay registros de asistencia')
    expect(empty).toContain('No hay datos de entregas')
    expect(empty).toContain('No hay evaluaciones en la versión')
    expect(empty).not.toContain('Pendientes')
    expect(empty).not.toContain('Tasa sobre días registrados')
  })
})
