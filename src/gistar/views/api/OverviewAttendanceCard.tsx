import type { Schemas } from '../../../shared/api/client'
import { Card, Empty, Metric, Notice } from '../../ui'

const days = new Intl.NumberFormat('es-ES', { maximumFractionDigits: 1 })
const rate = new Intl.NumberFormat('es-ES', { style: 'percent', maximumFractionDigits: 1 })
const date = new Intl.DateTimeFormat('es-ES', { dateStyle: 'medium', timeZone: 'UTC' })
const formatDays = (value: number | null | undefined) => value == null ? 'Sin dato' : days.format(value)

export function OverviewAttendanceCard({ attendance }: { attendance: Schemas['OverviewAttendance'] }) {
  const { totals, date_from: from, date_to: to } = attendance
  const period = [
    from && `Desde ${date.format(new Date(from))}`,
    to && `Hasta ${date.format(new Date(to))}`,
  ].filter(Boolean).join(' · ')
  return (
    <Card title="Asistencia">
      <p className="mb-3 text-sm text-muted">{period || 'Todas las fechas'}</p>
      {totals.suppressed || attendance.has_data === null ? (
        <Notice>No se muestran cifras de asistencia por el tamaño del grupo.</Notice>
      ) : attendance.has_data === false ? (
        <Empty>No hay registros de asistencia en este periodo.</Empty>
      ) : (
        <>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            <Metric label="Días asistidos" value={formatDays(totals.attended_days)} />
            <Metric label="Días con ausencia justificada" value={formatDays(totals.justified_absence_days)} />
            <Metric label="Días con ausencia sin justificar" value={formatDays(totals.unjustified_absence_days)} />
            <Metric label="Días sin registrar" value={formatDays(totals.unrecorded_days)} />
            <Metric label="Tasa sobre días registrados" value={totals.attendance_rate == null ? 'Sin dato' : rate.format(totals.attendance_rate)} />
          </div>
          <p className="mt-4 text-sm text-muted">{attendance.rule}</p>
        </>
      )}
    </Card>
  )
}
