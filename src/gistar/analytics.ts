import { addDays, dayOf, weekStart } from './dates'
import {
  type AttSummary,
  type DeliveryStatus,
  activeTasks,
  attendanceSummary,
  cohortCoders,
  deliveryStatus,
  effectiveCompetencies,
  evalIndex,
  levelAt,
  nowOf,
  reviewStatus,
  sessionsOf,
  todayOf,
} from './domain'
import type { Coder, Competencia, Evento, GistarData, Level } from './types'

export interface GroupFilters {
  cohortId: string
  from: string
  to: string
  /** null = every active competency of the cohort catalog */
  compIds: string[] | null
  tareaId: string | null
}
export interface EvoPoint {
  cut: string
  pairs: number
  evaluated: number
  mastered: number
  /** % of evaluated pairs at level 2 or 3; null when no data */
  mastery: number | null
  coverage: number | null
}
export interface Dist {
  comp: Competencia
  n1: number
  n2: number
  n3: number
  none: number
  N: number
}
export interface WeekAtt {
  week: string
  presente: number
  retraso: number
  ausente: number
  pendiente: number
  sessions: Evento[]
}

export const pct = (v: number | null | undefined, digits = 0) => (v == null ? '—' : `${(v * 100).toFixed(digits)}%`)
export const ratio = (a: number, b: number) => (b ? a / b : null)

export function weeklyCuts(from: string, to: string) {
  const cuts: string[] = []
  for (let c = addDays(weekStart(from), 6); c < to; c = addDays(c, 7)) cuts.push(c)
  cuts.push(to)
  return cuts
}

export function evolution(d: GistarData, coders: Coder[], comps: Competencia[], cuts: string[], tareaId: string | null, idx = evalIndex(d)): EvoPoint[] {
  return cuts.map((cut) => {
    let evaluated = 0
    let mastered = 0
    for (const c of coders)
      for (const k of comps) {
        const l = levelAt(idx, c.id, k.id, cut, tareaId)
        if (l === null) continue
        evaluated++
        if (l >= 2) mastered++
      }
    const pairs = coders.length * comps.length
    return { cut, pairs, evaluated, mastered, mastery: ratio(mastered, evaluated), coverage: ratio(evaluated, pairs) }
  })
}

export function groupAnalytics(d: GistarData, f: GroupFilters) {
  const today = todayOf(d)
  const now = nowOf(d)
  const to = f.to > today ? today : f.to
  const from = f.from > to ? to : f.from
  const coders = cohortCoders(d, f.cohortId).sort((a, b) => a.nombre_ficticio.localeCompare(b.nombre_ficticio, 'es'))
  const allComps = effectiveCompetencies(d, f.cohortId)
  const comps = f.compIds ? allComps.filter((c) => f.compIds!.includes(c.id)) : allComps
  const idx = evalIndex(d)

  const matrix = new Map<string, Map<string, Level | null>>()
  for (const c of coders) {
    const row = new Map<string, Level | null>()
    for (const k of comps) row.set(k.id, levelAt(idx, c.id, k.id, to, f.tareaId))
    matrix.set(c.id, row)
  }
  const dist: Dist[] = comps.map((comp) => {
    const r = { comp, n1: 0, n2: 0, n3: 0, none: 0, N: coders.length }
    for (const c of coders) {
      const l = matrix.get(c.id)!.get(comp.id)
      if (l === 1) r.n1++
      else if (l === 2) r.n2++
      else if (l === 3) r.n3++
      else r.none++
    }
    return r
  })
  const cuts = weeklyCuts(from, to)
  const evo = evolution(d, coders, comps, cuts, f.tareaId, idx)
  const current = evo[evo.length - 1]

  // Attendance (held sessions only, within range)
  const att: AttSummary = attendanceSummary(d, f.cohortId, { from, to })
  const sessionIds = new Set<string>()
  const weeks = new Map<string, WeekAtt>()
  const recs = new Map(d.asistencia.map((r) => [`${r.evento_id}|${r.coder_id}`, r.estado]))
  for (const s of sessionsOf(d, f.cohortId)) {
    const day = dayOf(s.inicio)
    if (s.inicio > now || day < from || day > to) continue
    sessionIds.add(s.id)
    const w = weekStart(day)
    const wk = weeks.get(w) ?? { week: w, presente: 0, retraso: 0, ausente: 0, pendiente: 0, sessions: [] }
    wk.sessions.push(s)
    for (const c of coders) wk[recs.get(`${s.id}|${c.id}`) ?? 'pendiente']++
    weeks.set(w, wk)
  }

  // Deliveries
  const tasks = activeTasks(d, f.cohortId).filter((t) =>
    f.tareaId ? t.id === f.tareaId : (dayOf(t.fecha_entrega) >= from && dayOf(t.fecha_entrega) <= to) || (f.to >= today && t.fecha_entrega > now),
  )
  const del: Record<DeliveryStatus, number> & { revision: number; total: number } = { a_tiempo: 0, tarde: 0, pendiente_en_plazo: 0, pendiente_vencida: 0, revision: 0, total: 0 }
  const coderIds = new Set(coders.map((c) => c.id))
  const perTask = tasks.map((t) => {
    const ents = d.entregas.filter((e) => e.tarea_id === t.id && coderIds.has(e.coder_id))
    let sent = 0
    for (const e of ents) {
      const st = deliveryStatus(e, t, now)
      del[st]++
      del.total++
      if (e.enviada_en) sent++
      if (e.enviada_en && reviewStatus(d, e) !== 'publicada') del.revision++
    }
    return { tarea: t, sent, total: ents.length, vencida: t.fecha_entrega <= now }
  })
  const dueTotal = del.a_tiempo + del.tarde + del.pendiente_vencida
  const alerts = d.alertas_simuladas.filter((a) => coderIds.has(a.coder_id) && a.estado === 'por_revisar')

  return {
    from,
    to,
    coders,
    comps,
    allComps,
    matrix,
    dist,
    evo,
    current,
    att,
    weeks: [...weeks.values()].sort((a, b) => a.week.localeCompare(b.week)),
    del,
    dueTotal,
    onTime: ratio(del.a_tiempo, dueTotal),
    perTask,
    alerts,
  }
}

export const MIN_CELL = 3
/** Aggregated, non-nominal indicators for coordination. Values are suppressed for small groups. */
export function cohortAggregate(d: GistarData, cohortId: string, minGroup: number) {
  const coh = d.cohortes.find((c) => c.id === cohortId)!
  const g = groupAnalytics(d, { cohortId, from: coh.inicio, to: todayOf(d), compIds: null, tareaId: null })
  return { coh, N: g.coders.length, suppressed: g.coders.length < minGroup, g }
}
