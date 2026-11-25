import type { Schemas } from '../../../shared/api/client'
import { SegmentLegend, StackedBar, levelSegments } from '../../components/charts'
import { Card, Empty, Notice } from '../../ui'

export function OverviewCompetenciesCard({ competencies }: { competencies: Schemas['OverviewCompetencies'] }) {
  const { distribution, framework_version: version, has_data: hasData, suppressed } = competencies
  return (
    <Card title="Competencias">
      {suppressed || hasData === null ? (
        <Notice>No se muestran cifras de competencias por el tamaño del grupo.</Notice>
      ) : version === null ? (
        <Empty>Esta cohorte aún no tiene un árbol de competencias asignado.</Empty>
      ) : !hasData || distribution.length === 0 ? (
        <Empty>No hay evaluaciones en la versión {version} del árbol de competencias.</Empty>
      ) : (
        <>
          <p className="mb-4 text-sm text-muted">Versión {version} del árbol de competencias. {competencies.rule}</p>
          <ul className="grid gap-4 lg:grid-cols-2">
            {distribution.map(({ codigo, nombre, counts }) => (
              <li key={codigo} className="space-y-2 rounded-xl border border-line p-4">
                <h3 className="text-sm font-semibold">{codigo} · {nombre}</h3>
                {counts ? <CompetencyDistribution counts={counts} /> : <p className="text-sm text-muted">Sin cifras disponibles</p>}
              </li>
            ))}
          </ul>
        </>
      )}
    </Card>
  )
}

function CompetencyDistribution({ counts }: { counts: Schemas['LevelCount'] }) {
  const segments = levelSegments({
    n1: counts.level_1, n2: counts.level_2, n3: counts.level_3, none: counts.not_assessed,
  })
  const total = segments.reduce((sum, segment) => sum + segment.value, 0)
  return (
    <>
      <StackedBar segments={segments} total={total} />
      <SegmentLegend segments={segments} total={total} />
    </>
  )
}
