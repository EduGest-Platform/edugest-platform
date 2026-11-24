import type { PublicCourse, PublicCoursePage } from '../../../shared/api/publicCatalog'
import { Button, Card, Field, Notice, inputCls } from '../../ui'

export type CatalogAdmissionFilter = '' | 'abierta' | 'cerrada'
export type PublicResource<T> = { status: 'loading' } | { status: 'error'; message: string } | { status: 'ready'; data: T }
export const COURSE_PAGE_SIZE = 20

/** Calendar dates have no time zone; never shift an application deadline to the previous day. */
export function courseDate(value: string) {
  return new Intl.DateTimeFormat('es-ES', { dateStyle: 'medium', timeZone: 'UTC' }).format(new Date(`${value}T12:00:00Z`))
}

export function PublicCourseList({ state, admission, offset, onFilter, onPage, onOpen, onRetry }: {
  state: PublicResource<PublicCoursePage>
  admission: CatalogAdmissionFilter
  offset: number
  onFilter: (filter: CatalogAdmissionFilter) => void
  onPage: (offset: number) => void
  onOpen: (course: PublicCourse) => void
  onRetry: () => void
}) {
  return <section aria-labelledby="public-catalog-title" className="grid gap-4">
    <header>
      <h1 id="public-catalog-title" className="text-2xl font-bold text-navy">Formaciones disponibles</h1>
      <p className="text-sm text-muted">Ofertas publicadas del servidor · Demostración con datos sintéticos.</p>
    </header>
    <Field label="Estado de convocatoria" htmlFor="public-admission-filter">
      <select id="public-admission-filter" className={inputCls} value={admission}
        onChange={(event) => onFilter(event.target.value as CatalogAdmissionFilter)}>
        <option value="">Todas las publicadas</option>
        <option value="abierta">Inscripción abierta</option>
        <option value="cerrada">Inscripción cerrada</option>
      </select>
    </Field>
    {state.status === 'loading' && <p role="status">Cargando formaciones…</p>}
    {state.status === 'error' && <div className="grid justify-items-start gap-3">
      <Notice tone="warning" live="assertive">{state.message}</Notice>
      <Button onClick={onRetry}>Volver a cargar formaciones</Button>
    </div>}
    {state.status === 'ready' && <>
      <p role="status" className="text-sm text-muted">{state.data.total} ofertas publicadas con este filtro.</p>
      {!state.data.items.length && <Notice live="polite">No hay formaciones en esta página con el filtro elegido. Prueba otro filtro o vuelve a la página anterior.</Notice>}
      <div className="grid gap-4 sm:grid-cols-2">
        {state.data.items.map((course) => <Card key={course.id}>
          <h2 className="text-lg font-bold text-navy">{course.name}</h2>
          <p className="text-sm text-muted">{course.program_name}</p>
          <p className="my-2 text-sm">Solicitud: <time dateTime={course.opens_on}>{courseDate(course.opens_on)}</time> – <time dateTime={course.closes_on}>{courseDate(course.closes_on)}</time></p>
          <p className="mb-3 text-sm">{course.admission_state === 'abierta' ? 'Inscripción abierta' : 'Inscripción cerrada'}</p>
          <Button variant="ghost" aria-label={`Ver formación: ${course.name}`} onClick={() => onOpen(course)}>Ver formación</Button>
        </Card>)}
      </div>
      <nav aria-label="Páginas del catálogo" className="flex flex-wrap items-center gap-3">
        <Button variant="ghost" disabled={offset === 0} onClick={() => onPage(Math.max(0, offset - COURSE_PAGE_SIZE))}>Página anterior</Button>
        <span className="text-sm">Página {Math.floor(offset / COURSE_PAGE_SIZE) + 1}</span>
        <Button variant="ghost" disabled={offset + COURSE_PAGE_SIZE >= state.data.total} onClick={() => onPage(offset + COURSE_PAGE_SIZE)}>Página siguiente</Button>
      </nav>
    </>}
  </section>
}
