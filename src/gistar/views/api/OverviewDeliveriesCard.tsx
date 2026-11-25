import type { Schemas } from '../../../shared/api/client'
import { Card, Empty, Notice, Table } from '../../ui'

export function OverviewDeliveriesCard({
  submissions,
  timezone,
}: {
  submissions: Schemas['OverviewSubmissions']
  timezone: string
}) {
  const formatDeadline = new Intl.DateTimeFormat('es-ES', { dateStyle: 'medium', timeStyle: 'short', timeZone: timezone })
  return (
    <Card title="Entregas">
      {submissions.suppressed || submissions.has_data === null ? (
        <Notice>No se muestran cifras de entregas por el tamaño del grupo.</Notice>
      ) : submissions.has_data === false || submissions.assignments.length === 0 ? (
        <Empty>No hay datos de entregas para las actividades publicadas de esta cohorte.</Empty>
      ) : (
        <>
          <Table head={['Actividad publicada', 'Plazo', 'A tiempo', 'Tarde', 'Pendientes', 'Vencidas', 'Revisadas']}>
            {submissions.assignments.map(assignment => (
              <tr key={assignment.assignment_id}>
                <td className="font-medium">{assignment.title}</td>
                <td className="whitespace-nowrap">{formatDeadline.format(new Date(assignment.due_at))}</td>
                {assignment.counts ? (
                  <>
                    <td>{assignment.counts.on_time}</td>
                    <td>{assignment.counts.late}</td>
                    <td>{assignment.counts.pending}</td>
                    <td>{assignment.counts.overdue}</td>
                    <td>{assignment.counts.reviewed}</td>
                  </>
                ) : <td colSpan={5}>Sin cifras disponibles</td>}
              </tr>
            ))}
          </Table>
          <p className="mt-4 text-sm text-muted">{submissions.rule} Las revisadas ya se incluyen en las entregadas.</p>
        </>
      )}
    </Card>
  )
}
