import { useEffect, useRef } from 'react'
import { ShieldAlert } from 'lucide-react'
import { describeApiError } from '../../shared/api/errors'
import { useGistar } from '../store'
import { Button } from '../ui'

/**
 * The screen people see when they are not allowed to open a page (error 403).
 * We move the keyboard focus to the title, so screen readers read it out loud.
 * The button always gives people a way back.
 */
/** `reason`: one sentence saying what is blocked. Example: "El registro de auditoría solo está disponible para algunos perfiles." */
export function AccessDenied({ reason }: { reason?: string }) {
  const { navigate } = useGistar()
  const headingRef = useRef<HTMLHeadingElement>(null)
  const problem = describeApiError(403)

  useEffect(() => {
    headingRef.current?.focus()
  }, [])

  return (
    <section aria-labelledby="access-denied-title" className="my-4 max-w-xl rounded-xl border border-amber-200 bg-amber-50/70 px-5 py-4 text-amber-950">
      <h2 id="access-denied-title" ref={headingRef} tabIndex={-1} className="flex items-center gap-2 text-base font-semibold outline-none">
        <ShieldAlert className="size-5 shrink-0 text-amber-700" aria-hidden />
        {problem.title}
      </h2>
      <p className="mt-2 text-sm leading-relaxed">
        {reason ? `${reason} ` : ''}
        {problem.hint}
      </p>
      <div className="mt-4">
        <Button variant="ghost" onClick={() => navigate('dashboard')}>
          Volver al inicio
        </Button>
      </div>
    </section>
  )
}
