import type { ReactNode } from 'react'
import { fmtDay } from '../dates'
import type { Level } from '../types'

export const LEVEL_STYLE: Record<Level | 0, { bg: string; fg: string; label: string }> = {
  0: { bg: '#ffffff', fg: '#8a98a8', label: 'Sin evaluar' },
  1: { bg: '#d9eeeb', fg: '#0f4e49', label: 'Nivel 1' },
  2: { bg: '#6dbdb3', fg: '#08332f', label: 'Nivel 2' },
  3: { bg: '#0f6e67', fg: '#ffffff', label: 'Nivel 3' },
}
export const HATCH = 'repeating-linear-gradient(135deg,#fff 0 5px,#eef2f5 5px 7px)'

export function LevelCell({ level, onClick, title }: { level: Level | null; onClick?: () => void; title?: string }) {
  const s = LEVEL_STYLE[level ?? 0]
  const body = level ? `N${level}` : '—'
  const cls = 'flex h-8 w-full min-w-10 items-center justify-center rounded-md text-xs font-semibold ring-1 ring-inset ring-black/5'
  const style = { background: level ? s.bg : HATCH, color: s.fg }
  return onClick ? (
    <button type="button" onClick={onClick} title={title} aria-label={title} className={`${cls} cursor-pointer transition hover:ring-2 hover:ring-blue`} style={style}>
      {body}
    </button>
  ) : (
    <span className={cls} style={style} title={title}>
      {body}
    </span>
  )
}

export function LevelLegend() {
  return (
    <div className="flex flex-wrap items-center gap-3 text-xs text-muted" aria-label="Leyenda de niveles">
      {([1, 2, 3, 0] as const).map((l) => (
        <span key={l} className="inline-flex items-center gap-1.5">
          <span className="inline-block size-3.5 rounded ring-1 ring-inset ring-black/10" style={{ background: l ? LEVEL_STYLE[l].bg : HATCH }} />
          {LEVEL_STYLE[l].label}
        </span>
      ))}
    </div>
  )
}

export interface Series {
  key: string
  label: string
  color: string
  dashed?: boolean
  values: (number | null)[]
}
/** Accessible multi-series line chart for proportions (0–1). Single points are drawn as dots only. */
export function LineChart({ labels, series, ariaLabel, height = 220, notes }: { labels: string[]; series: Series[]; ariaLabel: string; height?: number; notes?: string[] }) {
  const W = 640
  const H = height
  const pad = { l: 40, r: 14, t: 12, b: 28 }
  const iw = W - pad.l - pad.r
  const ih = H - pad.t - pad.b
  const x = (i: number) => pad.l + (labels.length <= 1 ? iw / 2 : (i * iw) / (labels.length - 1))
  const y = (v: number) => pad.t + ih - v * ih
  const step = Math.max(1, Math.ceil(labels.length / 8))
  return (
    <figure className="m-0">
      <svg viewBox={`0 0 ${W} ${H}`} className="h-auto w-full" role="img" aria-label={ariaLabel}>
        {[0, 0.25, 0.5, 0.75, 1].map((g) => (
          <g key={g}>
            <line x1={pad.l} x2={W - pad.r} y1={y(g)} y2={y(g)} stroke="#e7eef3" />
            <text x={pad.l - 8} y={y(g) + 4} textAnchor="end" fontSize="11" fill="#657587">
              {g * 100}%
            </text>
          </g>
        ))}
        {labels.map((l, i) =>
          i % step === 0 || i === labels.length - 1 ? (
            <text key={i} x={x(i)} y={H - 8} textAnchor="middle" fontSize="11" fill="#657587">
              {fmtDay(l)}
            </text>
          ) : null,
        )}
        {series.map((s) => {
          const segs: string[] = []
          let cur = ''
          s.values.forEach((v, i) => {
            if (v == null) {
              if (cur) segs.push(cur)
              cur = ''
            } else cur += `${cur ? 'L' : 'M'}${x(i)},${y(v)}`
          })
          if (cur) segs.push(cur)
          return (
            <g key={s.key}>
              {segs.map((p, i) => (
                <path key={i} d={p} fill="none" stroke={s.color} strokeWidth={2.25} strokeDasharray={s.dashed ? '5 4' : undefined} />
              ))}
              {s.values.map((v, i) =>
                v == null ? null : (
                  <circle key={i} cx={x(i)} cy={y(v)} r={3.5} fill="#fff" stroke={s.color} strokeWidth={2}>
                    <title>{`${s.label} · ${fmtDay(labels[i])}: ${Math.round(v * 100)}%${notes?.[i] ? ` (${notes[i]})` : ''}`}</title>
                  </circle>
                ),
              )}
            </g>
          )
        })}
      </svg>
      <figcaption className="mt-2 flex flex-wrap gap-4 text-xs text-muted">
        {series.map((s) => (
          <span key={s.key} className="inline-flex items-center gap-1.5">
            <svg width="18" height="6" aria-hidden>
              <line x1="0" x2="18" y1="3" y2="3" stroke={s.color} strokeWidth="2.5" strokeDasharray={s.dashed ? '4 3' : undefined} />
            </svg>
            {s.label}
          </span>
        ))}
      </figcaption>
    </figure>
  )
}

export interface Segment {
  key: string
  value: number
  color: string
  label: string
  pattern?: boolean
}
export function StackedBar({ segments, total, height = 'h-3' }: { segments: Segment[]; total: number; height?: string }) {
  return (
    <div className={`flex w-full overflow-hidden rounded-full bg-[#eef2f5] ${height}`} role="img" aria-label={segments.map((s) => `${s.label}: ${s.value} de ${total}`).join(', ')}>
      {total > 0 &&
        segments.map((s) =>
          s.value ? (
            <span key={s.key} title={`${s.label}: ${s.value}/${total}`} style={{ width: `${(100 * s.value) / total}%`, background: s.pattern ? HATCH : s.color }} className="h-full border-r border-white last:border-0" />
          ) : null,
        )}
    </div>
  )
}

export function SegmentLegend({ segments, total }: { segments: Segment[]; total?: number }) {
  return (
    <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted">
      {segments.map((s) => (
        <span key={s.key} className="inline-flex items-center gap-1.5">
          <span className="inline-block size-3 rounded-sm ring-1 ring-inset ring-black/10" style={{ background: s.pattern ? HATCH : s.color }} />
          {s.label}
          {total !== undefined && (
            <b className="font-semibold tabular-nums text-ink">
              {s.value}
            </b>
          )}
        </span>
      ))}
    </div>
  )
}

/** Stacked columns with a clickable button per column. */
export function ColumnChart({
  columns,
  ariaLabel,
  selected,
  onSelect,
}: {
  columns: { key: string; label: string; segments: Segment[]; caption?: ReactNode }[]
  ariaLabel: string
  selected?: string | null
  onSelect?: (key: string) => void
}) {
  const max = Math.max(1, ...columns.map((c) => c.segments.reduce((a, s) => a + s.value, 0)))
  return (
    <div role="group" aria-label={ariaLabel} className="flex h-48 items-end gap-1.5 overflow-x-auto pb-1">
      {columns.map((c) => {
        const tot = c.segments.reduce((a, s) => a + s.value, 0)
        return (
          <button
            key={c.key}
            type="button"
            onClick={() => onSelect?.(c.key)}
            aria-pressed={selected === c.key}
            aria-label={`${c.label}: ${c.segments.map((s) => `${s.label} ${s.value}`).join(', ')}`}
            className={`group flex h-full min-w-11 flex-1 cursor-pointer flex-col items-center justify-end gap-1 rounded-lg px-0.5 pt-1 ${selected === c.key ? 'bg-mist ring-1 ring-blue/30' : 'hover:bg-mist/60'}`}
          >
            <span className="flex w-full max-w-9 flex-col-reverse overflow-hidden rounded-md" style={{ height: `${(100 * tot) / max}%` }}>
              {c.segments.map((s) =>
                s.value ? <span key={s.key} title={`${s.label}: ${s.value}`} style={{ height: `${(100 * s.value) / tot}%`, background: s.pattern ? HATCH : s.color }} className="w-full border-t border-white first:border-0" /> : null,
              )}
            </span>
            <span className="whitespace-nowrap text-[10px] text-muted">{c.label}</span>
          </button>
        )
      })}
    </div>
  )
}

/** Individual competency timeline: discrete points only (no invented continuous trajectory). */
export function DotTimeline({
  from,
  to,
  points,
  markers = [],
  ariaLabel,
}: {
  from: string
  to: string
  points: { date: string; level: Level; label: string; legacy?: boolean }[]
  markers?: { date: string; label: string }[]
  ariaLabel: string
}) {
  const W = 420
  const H = 76
  const pad = { l: 26, r: 10, t: 10, b: 18 }
  const span = Math.max(1, (Date.parse(to) - Date.parse(from)) / 86400000)
  const x = (d: string) => pad.l + (((Date.parse(d) - Date.parse(from)) / 86400000) / span) * (W - pad.l - pad.r)
  const y = (l: number) => pad.t + ((3 - l) / 2) * (H - pad.t - pad.b)
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="h-auto w-full" role="img" aria-label={ariaLabel}>
      {[1, 2, 3].map((l) => (
        <g key={l}>
          <line x1={pad.l} x2={W - pad.r} y1={y(l)} y2={y(l)} stroke="#eef2f5" />
          <text x={pad.l - 8} y={y(l) + 4} textAnchor="end" fontSize="11" fill="#657587">
            N{l}
          </text>
        </g>
      ))}
      {markers.map((m) =>
        m.date >= from && m.date <= to ? (
          <g key={m.date + m.label}>
            <line x1={x(m.date)} x2={x(m.date)} y1={pad.t - 4} y2={H - pad.b} stroke="#e6b348" strokeDasharray="3 3" />
            <title>{m.label}</title>
          </g>
        ) : null,
      )}
      <text x={pad.l} y={H - 4} fontSize="10.5" fill="#657587">
        {fmtDay(from)}
      </text>
      <text x={W - pad.r} y={H - 4} fontSize="10.5" fill="#657587" textAnchor="end">
        {fmtDay(to)}
      </text>
      {points.map((p, i) => (
        <circle key={i} cx={x(p.date)} cy={y(p.level)} r={6} fill={p.legacy ? '#fff' : LEVEL_STYLE[p.level].bg} stroke="#0f6e67" strokeWidth={2} strokeDasharray={p.legacy ? '2 2' : undefined}>
          <title>{p.label}</title>
        </circle>
      ))}
    </svg>
  )
}
