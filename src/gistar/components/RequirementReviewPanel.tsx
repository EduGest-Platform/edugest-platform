import { CircleCheck, CircleDashed, CircleHelp, CircleX, ShieldQuestion } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import {
  REQUIREMENT_STATUS_TEXT,
  REVIEW_STATE_TEXT,
  summarizeReview,
  type RequirementCheck,
  type RequirementStatus,
  type ReviewState,
} from '../requirements'

/**
 * Colour and icon for each status. Same colour families as `Status` in ui.tsx, so the panel looks like the rest of the app.
 * The text label is always shown too, so colour is never the only signal.
 */
const STATUS_LOOK: Record<RequirementStatus, { icon: LucideIcon; cls: string }> = {
  pendiente: { icon: CircleDashed, cls: 'bg-slate-100 text-slate-700 ring-slate-500/20' },
  cumple: { icon: CircleCheck, cls: 'bg-teal-50 text-teal-800 ring-teal-600/20' },
  no_cumple: { icon: CircleX, cls: 'bg-amber-50 text-amber-800 ring-amber-600/25' },
  excepcion_en_revision: { icon: CircleHelp, cls: 'bg-violet-50 text-violet-800 ring-violet-600/20' },
  excepcion_aprobada: { icon: CircleCheck, cls: 'bg-teal-50 text-teal-800 ring-teal-600/20' },
}

/** Same boxes as `Notice` in ui.tsx (warning and info), plus the app's neutral mist for states with nothing to act on yet. */
const STATE_LOOK: Record<ReviewState, string> = {
  sin_revisar: 'border-line bg-mist/60 text-navy',
  en_revision: 'border-line bg-mist/60 text-navy',
  necesita_decision_humana: 'border-amber-200 bg-amber-50/70 text-amber-950',
  cumple: 'border-teal-200 bg-teal-50/60 text-teal-950',
}

/**
 * Shows the requirement review of one application on its dossier.
 * - `checks = null`: the source has no review data yet. We say so; we never invent data.
 * - `source = 'demo'`: synthetic examples from the local prototype, clearly labelled.
 */
export function RequirementReviewPanel({ checks, source }: { checks: readonly RequirementCheck[] | null; source: 'server' | 'demo' }) {
  if (checks === null) {
    return (
      <section aria-labelledby="req-title" className="rounded-xl border border-dashed border-line bg-[#fafcfd] px-4 py-3 text-sm">
        <h3 id="req-title" className="font-semibold">
          Revisión de requisitos
        </h3>
        <p className="mt-1 text-muted">La revisión de requisitos todavía no está disponible en el servidor. Cuando lo esté, aparecerá aquí.</p>
      </section>
    )
  }

  const summary = summarizeReview(checks)
  const text = REVIEW_STATE_TEXT[summary.state]

  return (
    <section aria-labelledby="req-title" className="grid gap-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 id="req-title" className="text-sm font-semibold">
          Revisión de requisitos
        </h3>
        {source === 'demo' && (
          <span className="rounded-md bg-[#fff0cc] px-2 py-0.5 text-[11px] font-bold text-[#6d5014]">Ejemplo local · sin servidor</span>
        )}
      </div>

      <div className={`rounded-xl border px-4 py-3 text-sm ${STATE_LOOK[summary.state]}`}>
        <p className="flex items-center gap-2 font-semibold">
          {summary.state === 'necesita_decision_humana' && <ShieldQuestion className="size-4 shrink-0" aria-hidden />}
          {text.title}
        </p>
        <p className="mt-1 leading-relaxed">{text.hint}</p>
        {summary.total > 0 && (
          <p className="mt-1 text-xs opacity-80">
            {summary.checked} de {summary.total} revisados
            {summary.openIssues > 0 && ` · ${summary.openIssues} ${summary.openIssues === 1 ? 'obligatorio pendiente de decisión' : 'obligatorios pendientes de decisión'}`}
          </p>
        )}
      </div>

      {checks.length > 0 && (
        <ul className="grid gap-2">
          {checks.map((c) => {
            const look = STATUS_LOOK[c.status]
            const Icon = look.icon
            return (
              <li key={c.id} className="rounded-lg border border-line px-3 py-2 text-sm">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span>
                    {c.label} <span className="text-xs text-muted">· {c.kind === 'obligatorio' ? 'Obligatorio' : 'Recomendado'}</span>
                  </span>
                  <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold ring-1 ring-inset ${look.cls}`}>
                    <Icon className="size-3.5" aria-hidden />
                    {REQUIREMENT_STATUS_TEXT[c.status]}
                  </span>
                </div>
                {c.note && <p className="mt-1 text-muted">{c.note}</p>}
                {c.reviewedBy && (
                  <p className="mt-0.5 text-xs text-muted">
                    Revisado por {c.reviewedBy}
                    {c.reviewedAt && ` · ${c.reviewedAt}`}
                  </p>
                )}
              </li>
            )
          })}
        </ul>
      )}
    </section>
  )
}
