import type { ButtonHTMLAttributes, ReactNode } from 'react'
import { Info, TriangleAlert } from 'lucide-react'
import { humanize } from './config'

export function PageTitle({ title, sub, eyebrow }: { title: string; sub: string; eyebrow?: string }) {
  return (
    <header className="mb-7">
      {eyebrow && <p className="mb-2 text-[11px] font-semibold uppercase tracking-[0.14em] text-teal-700">{eyebrow}</p>}
      <h1 className="text-[28px] font-bold leading-tight tracking-tight text-ink">{title}</h1>
      <p className="mt-1.5 max-w-2xl text-[15px] text-muted">{sub}</p>
    </header>
  )
}

export function Card({
  title,
  action,
  children,
  className = '',
}: {
  title?: ReactNode
  action?: ReactNode
  children: ReactNode
  className?: string
}) {
  return (
    <section className={`min-w-0 rounded-2xl border border-line bg-white p-6 shadow-[0_1px_2px_rgba(20,37,54,0.04)] ${className}`}>
      {(title || action) && (
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          {title && <h2 className="text-[17px] font-semibold tracking-tight text-ink">{title}</h2>}
          {action}
        </div>
      )}
      {children}
    </section>
  )
}

type Variant = 'primary' | 'ghost' | 'success' | 'subtle'
const variants: Record<Variant, string> = {
  primary: 'bg-blue text-white hover:bg-[#1d5a7d]',
  ghost: 'bg-mist text-navy hover:bg-[#e1ebf2]',
  success: 'bg-teal text-white hover:bg-[#0f776f]',
  subtle: 'bg-transparent text-muted hover:bg-mist hover:text-navy',
}
export function Button({
  variant = 'primary',
  size = 'md',
  className = '',
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; size?: 'sm' | 'md' }) {
  return (
    <button
      type="button"
      {...props}
      className={`inline-flex cursor-pointer items-center justify-center gap-2 rounded-xl font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${
        size === 'sm' ? 'px-3 py-1.5 text-[13px]' : 'px-4 py-2.5 text-sm'
      } ${variants[variant]} ${className}`}
    />
  )
}

const toneByState: Record<string, string> = {
  admitida: 'bg-teal-50 text-teal-800 ring-teal-600/20',
  completada: 'bg-teal-50 text-teal-800 ring-teal-600/20',
  en_seguimiento: 'bg-teal-50 text-teal-800 ring-teal-600/20',
  entregada: 'bg-teal-50 text-teal-800 ring-teal-600/20',
  enviada: 'bg-sky-50 text-sky-800 ring-sky-600/20',
  no_admitida: 'bg-rose-50 text-rose-800 ring-rose-600/20',
  fuera_de_plazo: 'bg-rose-50 text-rose-800 ring-rose-600/20',
  por_revisar: 'bg-amber-50 text-amber-800 ring-amber-600/25',
  pendiente_decision_humana: 'bg-amber-50 text-amber-800 ring-amber-600/25',
  lista_espera: 'bg-violet-50 text-violet-800 ring-violet-600/20',
  borrador: 'bg-slate-100 text-slate-700 ring-slate-500/20',
}
export function Status({ s, label }: { s: string | null | undefined; label?: string }) {
  const tone = toneByState[s ?? ''] ?? 'bg-mist text-[#255c81] ring-[#255c81]/15'
  const text = label ?? humanize(s)
  return (
    <span className={`inline-flex items-center whitespace-nowrap rounded-full px-2.5 py-0.5 text-xs font-semibold ring-1 ring-inset ${tone}`}>
      {text.charAt(0).toUpperCase() + text.slice(1)}
    </span>
  )
}

export function Notice({ tone = 'info', children }: { tone?: 'info' | 'warning'; children: ReactNode }) {
  const Icon = tone === 'warning' ? TriangleAlert : Info
  return (
    <div
      className={`my-4 flex gap-3 rounded-xl border px-4 py-3 text-sm leading-relaxed ${
        tone === 'warning' ? 'border-amber-200 bg-amber-50/70 text-amber-950' : 'border-teal-200 bg-teal-50/60 text-teal-950'
      }`}
    >
      <Icon className={`mt-0.5 size-4 shrink-0 ${tone === 'warning' ? 'text-amber-600' : 'text-teal-600'}`} aria-hidden />
      <div>{children}</div>
    </div>
  )
}

export function Field({ label, htmlFor, children, hint }: { label: string; htmlFor?: string; children: ReactNode; hint?: string }) {
  return (
    <div className="grid gap-1.5">
      <label htmlFor={htmlFor} className="text-[13px] font-semibold text-ink first-letter:uppercase">
        {label}
      </label>
      {children}
      {hint && <p className="text-xs text-muted">{hint}</p>}
    </div>
  )
}

export const inputCls =
  'w-full rounded-xl border border-[#ced9e3] bg-white px-3 py-2.5 text-sm text-ink placeholder:text-slate-400 disabled:bg-slate-50 disabled:text-slate-500 focus:border-blue focus:outline-none focus:ring-3 focus:ring-blue/15'

export function Table({ head, children }: { head: ReactNode[]; children: ReactNode }) {
  return (
    <div className="-mx-6 overflow-x-auto px-6">
      <table className="w-full min-w-[620px] border-collapse text-sm">
        <thead>
          <tr>
            {head.map((h, i) => (
              <th key={i} className="border-b border-line pb-2.5 pr-3 text-left text-xs font-semibold uppercase tracking-wide text-muted">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="[&_td]:border-b [&_td]:border-line [&_td]:py-3 [&_td]:pr-3 [&_td]:align-middle [&_tr:last-child_td]:border-0">
          {children}
        </tbody>
      </table>
    </div>
  )
}

export function Kpi({ label, value, icon }: { label: string; value: ReactNode; icon?: ReactNode }) {
  return (
    <div className="rounded-2xl border border-line bg-white p-5">
      <div className="flex items-center justify-between text-[13px] text-muted">
        {label}
        {icon}
      </div>
      <div className="mt-2 text-[30px] font-bold tracking-tight text-navy tabular-nums">{value}</div>
    </div>
  )
}

export function Progress({ value }: { value: number }) {
  return (
    <div className="h-1.5 w-full overflow-hidden rounded-full bg-[#e7eef3]" role="progressbar" aria-valuenow={Math.round(value)} aria-valuemin={0} aria-valuemax={100}>
      <span className="block h-full rounded-full bg-teal transition-[width]" style={{ width: `${value}%` }} />
    </div>
  )
}

export function SyntheticBadge() {
  return <span className="rounded-md bg-[#fff0cc] px-2 py-0.5 text-[11px] font-bold tracking-wide text-[#6d5014]">Datos sintéticos</span>
}

/** Short formula / denominator explanation, always visible as text (also as tooltip). */
export function Formula({ children }: { children: ReactNode }) {
  return <p className="mt-1.5 text-[11.5px] leading-snug text-muted">{children}</p>
}

export function Metric({ label, value, sub, formula, warn }: { label: string; value: ReactNode; sub?: ReactNode; formula?: string; warn?: string }) {
  return (
    <div className="min-w-0 rounded-2xl border border-line bg-white p-4" title={formula}>
      <div className="text-[12.5px] font-medium text-muted">{label}</div>
      <div className="mt-1 text-[26px] font-bold leading-tight tracking-tight text-navy tabular-nums">{value}</div>
      {sub && <div className="text-xs text-ink/70 tabular-nums">{sub}</div>}
      {formula && <Formula>{formula}</Formula>}
      {warn && <p className="mt-1.5 text-[11.5px] font-medium text-amber-700">{warn}</p>}
    </div>
  )
}

export function Empty({ children }: { children: ReactNode }) {
  return <div className="rounded-xl border border-dashed border-line bg-[#fafcfd] px-4 py-6 text-center text-sm text-muted">{children}</div>
}

export function Chips<T extends string>({ options, value, onChange, label }: { options: { id: T; label: string }[]; value: T[]; onChange: (v: T[]) => void; label: string }) {
  return (
    <div role="group" aria-label={label} className="flex flex-wrap gap-1.5">
      {options.map((o) => {
        const on = value.includes(o.id)
        return (
          <button
            key={o.id}
            type="button"
            aria-pressed={on}
            onClick={() => onChange(on ? value.filter((x) => x !== o.id) : [...value, o.id])}
            className={`cursor-pointer rounded-full border px-3 py-1 text-xs font-medium transition-colors ${on ? 'border-navy bg-navy text-white' : 'border-line bg-white text-ink/80 hover:border-blue/40'}`}
          >
            {o.label}
          </button>
        )
      })}
    </div>
  )
}

export function Segmented<T extends string>({ options, value, onChange, label }: { options: { id: T; label: string }[]; value: T; onChange: (v: T) => void; label: string }) {
  return (
    <div role="radiogroup" aria-label={label} className="inline-flex rounded-xl bg-mist p-1">
      {options.map((o) => (
        <button
          key={o.id}
          type="button"
          role="radio"
          aria-checked={value === o.id}
          onClick={() => onChange(o.id)}
          className={`cursor-pointer rounded-lg px-3 py-1.5 text-[13px] font-semibold transition-colors ${value === o.id ? 'bg-white text-navy shadow-sm' : 'text-muted hover:text-navy'}`}
        >
          {o.label}
        </button>
      ))}
    </div>
  )
}
