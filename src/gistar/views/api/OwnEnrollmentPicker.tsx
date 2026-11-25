import { useEffect, useState, type ReactNode } from 'react'
import { api, type Schemas } from '../../../shared/api/client'
import { describeApiError, problemText } from '../../../shared/api/errors'
import { Button, Empty, Field, Notice, inputCls } from '../../ui'

type Enrollment = Schemas['LearnerEnrollment']
type DataState<T> = { data: T } | { error: string } | null

const enrollmentStatus: Record<Enrollment['status'], string> = {
  activa: 'Activa',
  finalizada: 'Finalizada',
  baja_voluntaria: 'Baja voluntaria',
}

export function requireLearnerResponse<T>({ data, response, error }: { data?: T; response: Response; error?: unknown }): T {
  if (data === undefined) throw new Error(problemText(describeApiError(response.status, error)))
  return data
}

export function useLearnerRead<T>(load: (signal: AbortSignal) => Promise<T>) {
  const [state, setState] = useState<DataState<T>>(null)
  const [attempt, setAttempt] = useState(0)
  useEffect(() => {
    const controller = new AbortController()
    void load(controller.signal).then(data => {
      if (!controller.signal.aborted) setState({ data })
    }).catch(error => {
      if (controller.signal.aborted) return
      const message = error instanceof TypeError
        ? problemText(describeApiError(undefined))
        : error instanceof Error ? error.message : 'No se pudo cargar la información académica.'
      setState({ error: message })
    })
    return () => controller.abort()
  }, [load, attempt])
  return {
    state,
    retry() {
      setState(null)
      setAttempt(previous => previous + 1)
    },
  }
}

export function LearnerReadProblem({ message, retry }: { message: string; retry: () => void }) {
  return (
    <div className="space-y-3">
      <Notice tone="warning" live="polite">{message}</Notice>
      <Button variant="ghost" onClick={retry}>Reintentar</Button>
    </div>
  )
}

async function loadEnrollments(signal: AbortSignal) {
  return requireLearnerResponse(await api.GET('/api/v1/me/enrollments', { signal })).items
}

export function OwnEnrollmentPicker({ fieldId, children }: {
  fieldId: string
  children: (enrollment: Enrollment) => ReactNode
}) {
  const { state, retry } = useLearnerRead(loadEnrollments)
  const [selectedId, setSelectedId] = useState('')
  if (!state) return <p role="status" className="text-muted">Cargando matrículas…</p>
  if ('error' in state) return <LearnerReadProblem message={state.error} retry={retry} />

  const enrollments = state.data
  const selected = enrollments.find(item => item.enrollment_id === selectedId)
    ?? enrollments.find(item => item.status === 'activa') ?? enrollments[0]
  if (!selected) return <Empty>No tienes matrículas asociadas.</Empty>

  return (
    <>
      <Field label="Matrícula" htmlFor={fieldId}>
        <select id={fieldId} className={`${inputCls} max-w-md`} value={selected.enrollment_id}
          onChange={event => setSelectedId(event.target.value)}>
          {enrollments.map(item => (
            <option key={item.enrollment_id} value={item.enrollment_id}>
              {item.cohort_name} · {enrollmentStatus[item.status]}
            </option>
          ))}
        </select>
      </Field>
      {selected.status === 'activa' ? children(selected) : <Empty>Esta matrícula no está activa.</Empty>}
    </>
  )
}
