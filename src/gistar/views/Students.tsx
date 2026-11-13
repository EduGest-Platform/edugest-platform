import { pct } from '../analytics'
import { attendanceSummary, cohortCoders, effectiveCompetencies, evalIndex, levelAt, nominalCohorts, todayOf } from '../domain'
import { useGistar } from '../store'
import { Button, Card, Field, PageTitle, Progress, Table, inputCls } from '../ui'

export function StudentList() {
  const { data, role, navigate, setFocusStudent, setFocusComp, teacherCohort, setTeacherCohort } = useGistar()
  const cohorts = nominalCohorts(data, role)
  const cohortId = cohorts.some((c) => c.id === teacherCohort) ? teacherCohort : cohorts[0]?.id
  const coders = cohortCoders(data, cohortId)
  const comps = effectiveCompetencies(data, cohortId)
  const idx = evalIndex(data)
  const today = todayOf(data)
  return (
    <>
      <PageTitle title="Alumnado" sub="Coders de tus cohortes asignadas. Abre la ficha para ver su evolución competencial." />
      <Card
        title="Coders matriculados"
        action={
          <Field label="Cohorte" htmlFor="st-coh">
            <select id="st-coh" className={`${inputCls} w-auto`} value={cohortId} onChange={(e) => setTeacherCohort(e.target.value)}>
              {cohorts.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.nombre}
                </option>
              ))}
            </select>
          </Field>
        }
      >
        <Table head={['Coder', 'Asistencia', 'Competencias con datos', 'En nivel 2–3', '']}>
          {coders.map((s) => {
            const a = attendanceSummary(data, cohortId, { coderId: s.id })
            const lv = comps.map((c) => levelAt(idx, s.id, c.id, today))
            const withData = lv.filter((l) => l !== null).length
            return (
              <tr key={s.id}>
                <td>
                  <span className="mr-2 font-mono text-xs text-muted">{s.id}</span>
                  <span className="font-medium">{s.nombre_ficticio}</span>
                </td>
                <td className="tabular-nums">
                  {pct(a.tasa)} <span className="text-xs text-muted">({a.presente + a.retraso}/{a.registrados})</span>
                </td>
                <td>
                  <div className="flex items-center gap-3">
                    <div className="w-24">
                      <Progress value={comps.length ? (100 * withData) / comps.length : 0} />
                    </div>
                    <span className="text-xs tabular-nums text-muted">
                      {withData}/{comps.length}
                    </span>
                  </div>
                </td>
                <td className="tabular-nums">
                  {lv.filter((l) => (l ?? 0) >= 2).length}/{withData}
                </td>
                <td className="text-right">
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => {
                      setFocusStudent(s.id)
                      setFocusComp(null)
                      navigate('ficha')
                    }}
                  >
                    Ver ficha
                  </Button>
                </td>
              </tr>
            )
          })}
        </Table>
      </Card>
    </>
  )
}
