import type { PublicCourse } from '../../../shared/api/publicCatalog'
import { Button, Card, Notice } from '../../ui'
import { courseDate, type PublicResource } from './PublicCourseList'

export function PublicCourseDetail({ state, onBack, onRetry, onApply }: {
  state: PublicResource<PublicCourse>
  onBack: () => void
  onRetry: () => void
  onApply: (course: PublicCourse) => void
}) {
  return <section aria-labelledby="public-course-title" className="grid gap-4">
    <h1 id="public-course-title" tabIndex={-1} className="text-2xl font-bold text-navy">
      {state.status === 'ready' ? state.data.name : 'Ficha de formación'}
    </h1>
    <Button className="justify-self-start" variant="ghost" onClick={onBack}>Volver al catálogo</Button>
    {state.status === 'loading' && <p role="status">Cargando la ficha de formación…</p>}
    {state.status === 'error' && <>
      <Notice tone="warning" live="assertive">{state.message}</Notice>
      <Button onClick={onRetry}>Volver a cargar la ficha</Button>
    </>}
    {state.status === 'ready' && <Card>
      <p className="mb-3 font-medium">{state.data.program_name}</p>
      <dl className="grid gap-2 text-sm">
        <div><dt className="font-semibold">Apertura de solicitudes</dt><dd><time dateTime={state.data.opens_on}>{courseDate(state.data.opens_on)}</time></dd></div>
        <div><dt className="font-semibold">Cierre de solicitudes</dt><dd><time dateTime={state.data.closes_on}>{courseDate(state.data.closes_on)}</time></dd></div>
        <div><dt className="font-semibold">Plazas ofertadas</dt><dd>{state.data.capacity}</dd></div>
      </dl>
      <p className="my-4 text-sm">{state.data.admission_state === 'abierta' ? 'Inscripción abierta. Enviar una solicitud no garantiza una plaza.' : 'Inscripción cerrada. Puedes consultar otras formaciones en el catálogo.'}</p>
      {state.data.admission_state === 'abierta' && <Button onClick={() => onApply(state.data)}>Solicitar plaza</Button>}
      <p className="mt-4 text-xs text-muted">Datos sintéticos del servidor. Requisitos y contenidos adicionales pendientes de publicación; no se deducen de esta ficha.</p>
    </Card>}
  </section>
}
