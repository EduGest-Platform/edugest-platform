import { useEffect, useRef, useState, type FormEvent } from 'react'
import { api, errorMessage, type Schemas } from '../../../shared/api/client'
import { humanize } from '../../config'
import { Button, Card, Field, Notice, PageTitle, inputCls } from '../../ui'
import { useAcademicCohorts, type AcademicCohort } from './ApiCohorts'
import { CompetencyFrameworkEditor } from './CompetencyFrameworkEditor'

type Framework = Schemas['FrameworkOut']
type Learner = Schemas['CompetencyLearner']
type Assessment = Schemas['EnrollmentAssessments']
type ScopeData = { versions: Framework[]; assigned: Framework | null; learners: Learner[] }
const dateTime = new Intl.DateTimeFormat('es-ES', { dateStyle: 'short', timeStyle: 'short', timeZone: 'Europe/Madrid' })

function useScopedRequest() {
  const pending = useRef<AbortController | null>(null)
  useEffect(() => () => pending.current?.abort(), [])
  return pending
}

function LearnerAssessments({ learner, framework }: { learner: Learner; framework: Framework | null }) {
  const [record, setRecord] = useState<Assessment | null>(null)
  const [competency, setCompetency] = useState('')
  const [level, setLevel] = useState<Schemas['AssessmentWrite']['level']>(1)
  const [evidence, setEvidence] = useState('')
  const [attempt, setAttempt] = useState(0)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [busy, setBusy] = useState(false)
  const pending = useScopedRequest()
  const path = { enrollment_id: learner.enrollment_id }

  useEffect(() => {
    const controller = new AbortController()
    void api.GET('/api/v1/enrollments/{enrollment_id}/assessments', {
      params: { path: { enrollment_id: learner.enrollment_id } }, signal: controller.signal,
    }).then(({ data, error }) => {
      if (controller.signal.aborted) return
      if (data) setRecord(data)
      else setError(errorMessage(error, 'No se pudieron leer las evaluaciones.'))
    }).catch(() => {
      if (!controller.signal.aborted) setError('No se pudo conectar con el servidor.')
    })
    return () => controller.abort()
  }, [learner.enrollment_id, attempt])

  const selected = framework?.competencies.find(item => item.id === competency) ?? framework?.competencies[0]

  async function assess(event: FormEvent) {
    event.preventDefault()
    if (!selected || !evidence.trim() || pending.current) return
    const controller = new AbortController()
    pending.current = controller
    setBusy(true)
    setError('')
    setNotice('')
    try {
      const { data, error } = await api.POST('/api/v1/enrollments/{enrollment_id}/assessments', {
        params: { path }, body: { competency_id: selected.id, level, evidence: evidence.trim() }, signal: controller.signal,
      })
      if (controller.signal.aborted) return
      if (!data) setError(errorMessage(error, 'No se pudo guardar la evaluación.'))
      else {
        setNotice('Evaluación guardada.')
        setEvidence('')
        setRecord(null)
        setAttempt(value => value + 1)
      }
    } catch {
      if (!controller.signal.aborted) setError('No se pudo confirmar el registro. Actualiza el historial antes de reintentar.')
    } finally {
      pending.current = null
      if (!controller.signal.aborted) setBusy(false)
    }
  }

  return (
    <div className="grid gap-4">
      {error && <Notice tone="warning" live="assertive">{error}</Notice>}
      {notice && <p role="status">{notice}</p>}
      {error && <Button variant="ghost" className="justify-self-start" disabled={busy} onClick={() => {
        setError(''); setRecord(null); setAttempt(value => value + 1)
      }}>Actualizar evaluaciones</Button>}
      {!record && !error && <p role="status">Cargando evaluaciones…</p>}
      {record && (
        <>
          {record.current.length > 0 && <ul className="grid gap-2">
            {record.current.map(item => (
              <li key={item.competency_id} className="flex flex-wrap justify-between gap-2 border-b border-line pb-2 text-sm">
                <span>{item.codigo} · {item.nombre}</span>
                <span>{item.level === null ? 'Sin evaluar' : `Nivel ${item.level}`}</span>
              </li>
            ))}
          </ul>}
          {selected && record.framework_version === framework?.version && (
            <form className="grid gap-3 rounded-xl bg-mist/60 p-3" onSubmit={assess}>
              <div className="grid gap-3 sm:grid-cols-2">
                <Field label="Competencia" htmlFor="assessment-competency">
                  <select id="assessment-competency" className={inputCls} value={selected.id} disabled={busy}
                    onChange={event => setCompetency(event.target.value)}>
                    {framework?.competencies.map(item => <option key={item.id} value={item.id}>{item.codigo} · {item.nombre}</option>)}
                  </select>
                </Field>
                <Field label="Nivel" htmlFor="assessment-level">
                  <select id="assessment-level" className={inputCls} value={level} disabled={busy}
                    onChange={event => setLevel(Number(event.target.value) as typeof level)}>
                    {[1, 2, 3].map(value => <option key={value} value={value}>Nivel {value}</option>)}
                  </select>
                </Field>
              </div>
              <p className="text-sm">{[selected.level_1, selected.level_2, selected.level_3][level - 1]}</p>
              <Field label="Evidencia" htmlFor="assessment-evidence">
                <textarea id="assessment-evidence" className={inputCls} required maxLength={500}
                  readOnly={busy} value={evidence} onChange={event => setEvidence(event.target.value)} />
              </Field>
              <Button className="justify-self-start" type="submit" disabled={busy || !evidence.trim()}>Guardar evaluación</Button>
            </form>
          )}
          {record.framework_version !== (framework?.version ?? null) &&
            <Notice tone="warning">La versión asignada cambió. Actualiza la cohorte antes de evaluar.</Notice>}
          <h3 className="font-semibold">Historial de evaluaciones</h3>
          {record.history.length ? (
            <ul className="grid gap-2">
              {[...record.history].reverse().map(item => <li key={item.id} className="rounded-xl border border-line p-3 text-sm">
                <p className="font-medium">{item.codigo} · Nivel {item.level} · v{item.framework_version}</p>
                <p className="text-xs text-muted">{item.assessed_by ?? 'Equipo docente'} · {dateTime.format(new Date(item.assessed_at))}</p>
                <p className="mt-2 whitespace-pre-wrap wrap-anywhere">{item.evidence}</p>
              </li>)}
            </ul>
          ) : <p className="text-sm text-muted">Todavía no hay evaluaciones.</p>}
        </>
      )}
    </div>
  )
}

function CompetencyWorkspace({ cohort }: { cohort: AcademicCohort }) {
  const [data, setData] = useState<ScopeData | null>(null)
  const [attempt, setAttempt] = useState(0)
  const [learnerId, setLearnerId] = useState('')
  const [editor, setEditor] = useState<Framework | null | undefined>(undefined)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [busy, setBusy] = useState(false)
  const pending = useScopedRequest()
  const { id, program_id } = cohort

  useEffect(() => {
    const controller = new AbortController()
    const scope = { params: { path: { cohort_id: id } }, signal: controller.signal }
    void Promise.all([
      api.GET('/api/v1/programs/{program_id}/competency-frameworks', { params: { path: { program_id } }, signal: controller.signal }),
      api.GET('/api/v1/cohorts/{cohort_id}/competencies', scope),
      api.GET('/api/v1/cohorts/{cohort_id}/competency-roster', scope),
    ]).then(([versions, active, roster]) => {
      if (controller.signal.aborted) return
      if (!versions.data || !active.data || !roster.data) {
        setError(errorMessage(versions.error ?? active.error ?? roster.error, 'No se pudo cargar la cohorte.'))
      } else {
        setData({ versions: versions.data.items, assigned: active.data.framework, learners: roster.data.items })
      }
    }).catch(() => {
      if (!controller.signal.aborted) setError('No se pudo conectar con el servidor.')
    })
    return () => controller.abort()
  }, [id, program_id, attempt])

  function reload() {
    setError('')
    setData(null)
    setAttempt(value => value + 1)
  }

  async function change(send: (signal: AbortSignal) => Promise<{ data?: unknown; error?: unknown }>, message: string) {
    if (pending.current) return
    const controller = new AbortController()
    pending.current = controller
    setBusy(true)
    setError('')
    setNotice('')
    try {
      const { data, error } = await send(controller.signal)
      if (controller.signal.aborted) return
      if (!data) setError(errorMessage(error, 'No se pudo guardar el marco.'))
      else {
        setEditor(undefined)
        setNotice(message)
        reload()
      }
    } catch {
      if (!controller.signal.aborted) setError('No se pudo confirmar el cambio. Actualiza la cohorte antes de reintentar.')
    } finally {
      pending.current = null
      if (!controller.signal.aborted) setBusy(false)
    }
  }

  const learner = data?.learners.find(item => item.enrollment_id === learnerId)

  return (
    <>
      {error && <Notice tone="warning" live="assertive">{error}</Notice>}
      {notice && <p role="status">{notice}</p>}
      <Card title="Marco de competencias" action={<Button variant="ghost" onClick={reload} disabled={busy}>Actualizar cohorte</Button>}>
        {!data && !error && <p role="status">Cargando marco y matrículas…</p>}
        {data && (
          <div className="grid gap-4">
            <p>{data.assigned ? `Versión asignada a la cohorte: v${data.assigned.version}.` : 'Esta cohorte aún no tiene un marco asignado.'}</p>
            <ul className="grid gap-2">
              {[...data.versions].reverse().map(version => (
                <li key={version.id} className="flex flex-wrap items-center gap-2 border-b border-line pb-2 text-sm">
                  <span className="mr-auto">Versión {version.version} · {humanize(version.estado)} · {version.competencies.length} competencias</span>
                  {version.estado === 'borrador' && <>
                    <Button size="sm" variant="ghost" disabled={busy} onClick={() => setEditor(version)}>Editar borrador</Button>
                    <Button size="sm" disabled={busy || editor !== undefined} onClick={() => void change(
                      signal => api.POST('/api/v1/competency-frameworks/{framework_id}/publish', {
                        params: { path: { framework_id: version.id } }, signal,
                      }), 'Versión publicada.',
                    )}>Publicar versión</Button>
                  </>}
                  {version.estado === 'publicada' && version.id !== data.assigned?.id && (
                    <Button size="sm" disabled={busy || editor !== undefined} onClick={() => void change(
                      signal => api.PUT('/api/v1/cohorts/{cohort_id}/competency-framework', {
                        params: { path: { cohort_id: id } }, body: { framework_id: version.id }, signal,
                      }), 'Marco asignado a la cohorte.',
                    )}>Asignar a esta cohorte</Button>
                  )}
                </li>
              ))}
            </ul>
            {editor === undefined && <Button className="justify-self-start" variant="ghost" disabled={busy}
              onClick={() => setEditor(null)}>Crear borrador</Button>}
            {editor !== undefined && (
              <CompetencyFrameworkEditor key={editor?.id ?? 'new'} draft={editor} busy={busy}
                onClose={() => setEditor(undefined)} onSave={body => void change(
                  signal => editor
                    ? api.PUT('/api/v1/competency-frameworks/{framework_id}/competencies', { params: { path: { framework_id: editor.id } }, body, signal })
                    : api.POST('/api/v1/programs/{program_id}/competency-frameworks', { params: { path: { program_id } }, body, signal }),
                  'Borrador guardado.',
                )} />
            )}
          </div>
        )}
      </Card>
      {data && <Card title="Evaluaciones">
        <div className="grid gap-4">
          {data.learners.length ? (
            <Field label="Matrícula" htmlFor="competency-learner">
              <select id="competency-learner" className={inputCls} value={learnerId} onChange={event => setLearnerId(event.target.value)}>
                <option value="">Selecciona una matrícula</option>
                {data.learners.map(item => <option key={item.enrollment_id} value={item.enrollment_id}>{item.display_name}</option>)}
              </select>
            </Field>
          ) : <p className="text-sm text-muted">No hay matrículas para evaluar en esta cohorte.</p>}
          {learner && <LearnerAssessments key={learner.enrollment_id} learner={learner} framework={data.assigned} />}
        </div>
      </Card>}
    </>
  )
}

export function ApiCompetencies() {
  const { cohorts, loading, error, retry } = useAcademicCohorts()
  const [selected, setSelected] = useState('')
  const cohort = cohorts.find(item => item.id === selected) ?? cohorts[0]
  return (
    <div className="space-y-4">
      <PageTitle title="Competencias" sub="Gestiona el marco del programa y registra evaluaciones dentro de tus cohortes." />
      {loading && <p role="status">Cargando cohortes…</p>}
      {error && <><Notice tone="warning" live="assertive">{error}</Notice><Button onClick={retry}>Volver a cargar</Button></>}
      {!loading && !error && !cohort && <p>No hay cohortes disponibles en tu ámbito.</p>}
      {cohort && <>
        <Card>
          <Field label="Cohorte" htmlFor="competency-cohort">
            <select id="competency-cohort" className={inputCls} value={cohort.id} onChange={event => setSelected(event.target.value)}>
              {cohorts.map(item => <option key={item.id} value={item.id}>{item.nombre}</option>)}
            </select>
          </Field>
        </Card>
        <CompetencyWorkspace key={cohort.id} cohort={cohort} />
      </>}
    </div>
  )
}
