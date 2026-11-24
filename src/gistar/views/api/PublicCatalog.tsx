import { useCallback, useEffect, useState } from 'react'
import { publicCatalog, type PublicCourse } from '../../../shared/api/publicCatalog'
import { PublicCourseList, COURSE_PAGE_SIZE, type CatalogAdmissionFilter, type PublicResource } from './PublicCourseList'
import { PublicCourseDetail } from './PublicCourseDetail'
import { observePublicRead } from './publicCatalogResource'

function usePublicRead<T>(key: string, load: (signal: AbortSignal) => Promise<T>): PublicResource<T> {
  const [result, setResult] = useState<{ key: string; state: PublicResource<T> }>({ key, state: { status: 'loading' } })
  useEffect(() => observePublicRead(load, (state) => setResult({ key, state })), [key, load])
  return result.key === key ? result.state : { status: 'loading' }
}

function CourseList({ admission, offset, onFilter, onPage, onOpen }: {
  admission: CatalogAdmissionFilter; offset: number
  onFilter: (filter: CatalogAdmissionFilter) => void; onPage: (offset: number) => void
  onOpen: (course: PublicCourse) => void
}) {
  const [attempt, setAttempt] = useState(0)
  const load = useCallback((signal: AbortSignal) => publicCatalog.list({ admissionState: admission || undefined,
    offset, limit: COURSE_PAGE_SIZE }, signal), [admission, offset])
  const state = usePublicRead(`${admission}:${offset}:${attempt}`, load)
  return <PublicCourseList state={state} admission={admission} offset={offset} onFilter={onFilter}
    onPage={onPage} onOpen={onOpen} onRetry={() => setAttempt((value) => value + 1)} />
}

function CourseDetail({ id, onBack, onApply }: { id: string; onBack: () => void; onApply: (course: PublicCourse) => void }) {
  const [attempt, setAttempt] = useState(0)
  const load = useCallback((signal: AbortSignal) => publicCatalog.get(id, signal), [id])
  const state = usePublicRead(`${id}:${attempt}`, load)
  return <PublicCourseDetail state={state} onBack={onBack} onApply={onApply} onRetry={() => setAttempt((value) => value + 1)} />
}

export function PublicCatalog({ onApply }: { onApply: (course: PublicCourse) => void }) {
  const [admission, setAdmission] = useState<CatalogAdmissionFilter>('')
  const [offset, setOffset] = useState(0)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  useEffect(() => {
    document.getElementById(selectedId ? 'public-course-title' : 'public-catalog-title')?.focus()
  }, [selectedId])
  return selectedId
    ? <CourseDetail key={selectedId} id={selectedId} onBack={() => setSelectedId(null)} onApply={onApply} />
    : <CourseList admission={admission} offset={offset} onFilter={(filter) => { setAdmission(filter); setOffset(0) }}
      onPage={setOffset} onOpen={(course) => setSelectedId(course.id)} />
}
