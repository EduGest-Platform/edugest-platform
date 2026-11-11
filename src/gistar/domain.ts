import { addDays, dayOf, weekStart } from './dates'
import type {
  AsistEstado,
  CalItem,
  Coder,
  Competencia,
  Entrega,
  Evaluacion,
  GistarData,
  Level,
  Revision,
  Role,
  Tarea,
} from './types'

/** Demo identity per role. Real access control would require backend + authentication. */
export const DEMO_USER: Record<Role, string> = {
  admin: 'USR-ADM',
  docente: 'USR-DOC',
  coder: 'USR-COD',
  aspirante: 'USR-ASP',
  fundacion: 'USR-FUND',
  seleccion: 'USR-SEL',
  coordinacion: 'USR-COORD',
}
export const CODER_ID = 'E-001'
export const ASPIRANT_ID = 'A-001'
/** Minimum group size for coordination aggregates (k-anonymity style suppression). */
export const MIN_GROUP = 5
export const ABSENCE_RULE = { window: 6, threshold: 3 }

export const todayOf = (d: GistarData) => d.meta.fecha_simulada
export const nowOf = (d: GistarData) => `${d.meta.fecha_simulada}T12:00`

export const userName = (d: GistarData, id: string) => d.usuarios_demo.find((u) => u.id === id)?.nombre ?? id
export const coderName = (d: GistarData, id: string) => d.coders.find((c) => c.id === id)?.nombre_ficticio ?? id
export const cohortOf = (d: GistarData, id: string) => d.cohortes.find((c) => c.id === id)
export const programOf = (d: GistarData, id: string) => d.programas.find((p) => p.id === id)

/** Cohorts whose nominal data the role may see. */
export function nominalCohorts(d: GistarData, role: Role) {
  if (role === 'docente') return d.cohortes.filter((c) => c.docente_responsable === DEMO_USER.docente)
  if (role === 'admin') return d.cohortes
  return []
}
/** Programs whose catalog the role may configure. */
export function editablePrograms(d: GistarData, role: Role) {
  if (role === 'admin') return d.programas
  if (role === 'docente') {
    const ids = new Set(nominalCohorts(d, role).map((c) => c.programa_id))
    return d.programas.filter((p) => ids.has(p.id))
  }
  return []
}

export const cohortCoders = (d: GistarData, cohortId: string): Coder[] =>
  d.coders.filter((c) => c.cohorte_id === cohortId && c.estado === 'activo')

const byOrder = (a: Competencia, b: Competencia) => a.orden - b.orden || a.codigo.localeCompare(b.codigo, 'es', { numeric: true })

/** Program catalog (+ cohort-specific items) for one program. */
export const programCompetencies = (d: GistarData, programId: string) =>
  d.competencias.filter((c) => c.programa_id === programId).sort(byOrder)

/** Effective active catalog for a cohort: inherited program items not excluded + cohort-specific items. */
export function effectiveCompetencies(d: GistarData, cohortId: string, includeArchived = false) {
  const coh = cohortOf(d, cohortId)
  if (!coh) return []
  return d.competencias
    .filter(
      (c) =>
        c.programa_id === coh.programa_id &&
        (c.cohorte_id === null ? !coh.competencias_excluidas.includes(c.id) : c.cohorte_id === cohortId) &&
        (includeArchived || c.activo),
    )
    .sort(byOrder)
}

/** Next unique code in the program scope: C{max+1}. Codes are identifiers, not a closed list. */
export function nextCode(d: GistarData, programId: string) {
  const nums = d.competencias.filter((c) => c.programa_id === programId).map((c) => Number(/^C(\d+)$/.exec(c.codigo)?.[1] ?? 0))
  return `C${Math.max(0, ...nums) + 1}`
}
export function nextId(prefix: string, ids: string[]) {
  const nums = ids.map((i) => Number(i.slice(prefix.length).replace(/\D/g, '')) || 0)
  return `${prefix}${String(Math.max(0, ...nums) + 1).padStart(2, '0')}`
}
export const uid = (p: string) => `${p}-${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`

// ---------- Evaluations ----------
export const published = (e: Evaluacion) => e.estado === 'publicada'
const newer = (a: Evaluacion, b: Evaluacion) => a.fecha > b.fecha || (a.fecha === b.fecha && a.seq > b.seq)

/** Latest published evaluation up to and including `cut` (never uses future results). */
export function latestEval(evals: Evaluacion[], coderId: string, compId: string, cut: string, tareaId?: string | null) {
  let best: Evaluacion | undefined
  for (const e of evals) {
    if (e.coder_id !== coderId || e.competencia_id !== compId || !published(e) || e.fecha > cut) continue
    if (tareaId && e.tarea_id !== tareaId) continue
    if (!best || newer(e, best)) best = e
  }
  return best
}
export function evalIndex(d: GistarData) {
  const map = new Map<string, Evaluacion[]>()
  for (const e of d.evaluaciones) {
    if (!published(e)) continue
    const k = `${e.coder_id}|${e.competencia_id}`
    const arr = map.get(k)
    if (arr) arr.push(e)
    else map.set(k, [e])
  }
  for (const arr of map.values()) arr.sort((a, b) => (newer(a, b) ? 1 : -1))
  return map
}
/** Using a pre-built index; returns null when there is no data (never level 0). */
export function levelAt(idx: Map<string, Evaluacion[]>, coderId: string, compId: string, cut: string, tareaId?: string | null): Level | null {
  const arr = idx.get(`${coderId}|${compId}`)
  if (!arr) return null
  for (let i = arr.length - 1; i >= 0; i--) {
    const e = arr[i]
    if (e.fecha <= cut && (!tareaId || e.tarea_id === tareaId)) return e.nivel
  }
  return null
}
export const nextSeq = (d: GistarData) => Math.max(0, ...d.evaluaciones.map((e) => e.seq)) + 1

// ---------- Deliveries ----------
export type DeliveryStatus = 'a_tiempo' | 'tarde' | 'pendiente_en_plazo' | 'pendiente_vencida'
export function deliveryStatus(e: Entrega, t: Tarea, now: string): DeliveryStatus {
  if (e.enviada_en) return e.enviada_en <= t.fecha_entrega ? 'a_tiempo' : 'tarde'
  return now <= t.fecha_entrega ? 'pendiente_en_plazo' : 'pendiente_vencida'
}
export const DELIVERY_LABEL: Record<DeliveryStatus, string> = {
  a_tiempo: 'Entregada a tiempo',
  tarde: 'Entregada tarde',
  pendiente_en_plazo: 'Pendiente en plazo',
  pendiente_vencida: 'Pendiente vencida',
}
export const revisionsOf = (d: GistarData, entregaId: string) =>
  d.revisiones.filter((r) => r.entrega_id === entregaId).sort((a, b) => a.creada_en.localeCompare(b.creada_en))
export function reviewStatus(d: GistarData, e: Entrega): 'sin_entregar' | 'sin_revisar' | 'borrador' | 'publicada' {
  const revs = revisionsOf(d, e.id)
  const last = revs[revs.length - 1] as Revision | undefined
  if (last?.estado === 'borrador') return 'borrador'
  if (revs.some((r) => r.estado === 'publicada')) return 'publicada'
  return e.enviada_en ? 'sin_revisar' : 'sin_entregar'
}
export const activeTasks = (d: GistarData, cohortId?: string) =>
  d.tareas.filter((t) => t.estado === 'activa' && (!cohortId || t.cohorte_id === cohortId)).sort((a, b) => a.fecha_entrega.localeCompare(b.fecha_entrega))

// ---------- Attendance ----------
export const sessionsOf = (d: GistarData, cohortId: string) =>
  d.eventos.filter((e) => e.tipo === 'sesion' && e.estado !== 'cancelado' && e.cohorte_id === cohortId).sort((a, b) => a.inicio.localeCompare(b.inicio))

export interface AttSummary {
  celebradas: number
  presente: number
  retraso: number
  ausente: number
  pendiente: number
  registrados: number
  tasa: number | null
}
/** Rate = (presente + retraso) / confirmed records of held sessions. Future sessions and pending records never count as absences. */
export function attendanceSummary(d: GistarData, cohortId: string, opts: { coderId?: string; from?: string; to?: string } = {}): AttSummary {
  const now = nowOf(d)
  const sessions = sessionsOf(d, cohortId).filter(
    (s) => s.inicio <= now && (!opts.from || dayOf(s.inicio) >= opts.from) && (!opts.to || dayOf(s.inicio) <= opts.to),
  )
  const coders = opts.coderId ? [opts.coderId] : cohortCoders(d, cohortId).map((c) => c.id)
  const ids = new Set(sessions.map((s) => s.id))
  const recs = new Map<string, AsistEstado>()
  for (const r of d.asistencia) if (ids.has(r.evento_id)) recs.set(`${r.evento_id}|${r.coder_id}`, r.estado)
  const s: AttSummary = { celebradas: sessions.length, presente: 0, retraso: 0, ausente: 0, pendiente: 0, registrados: 0, tasa: null }
  for (const ses of sessions)
    for (const c of coders) {
      const st = recs.get(`${ses.id}|${c}`) ?? 'pendiente'
      s[st]++
    }
  s.registrados = s.presente + s.retraso + s.ausente
  s.tasa = s.registrados ? (s.presente + s.retraso) / s.registrados : null
  return s
}

/** Explainable, human-reviewed signal: ≥3 confirmed absences among the last 6 registered sessions. */
export function applyAbsenceRule(d: GistarData, coderId: string) {
  const coder = d.coders.find((c) => c.id === coderId)
  if (!coder) return
  const now = nowOf(d)
  const held = sessionsOf(d, coder.cohorte_id).filter((s) => s.inicio <= now)
  const regs = held
    .map((s) => d.asistencia.find((r) => r.evento_id === s.id && r.coder_id === coderId))
    .filter((r) => r && r.estado !== 'pendiente')
    .slice(-ABSENCE_RULE.window)
  const abs = regs.filter((r) => r!.estado === 'ausente').length
  const open = d.alertas_simuladas.some((a) => a.coder_id === coderId && a.estado !== 'cerrada')
  if (abs >= ABSENCE_RULE.threshold && !open) {
    d.alertas_simuladas.push({
      id: nextId('AL-', d.alertas_simuladas.map((a) => a.id)),
      coder_id: coderId,
      estado: 'por_revisar',
      senales: [`${abs} ausencias confirmadas en las últimas ${regs.length} sesiones registradas`],
      explicacion: `Regla ilustrativa: ${ABSENCE_RULE.threshold} o más ausencias confirmadas en las últimas ${ABSENCE_RULE.window} sesiones registradas. Las ausencias no prueban abandono; requiere conversación y revisión humana.`,
      creada_en: todayOf(d),
      plan_apoyo: null,
      es_prediccion_real: false,
    })
  }
}

// ---------- Calendar ----------
export const EVENT_TYPES: Record<CalItem['tipo'], { label: string; dot: string; chip: string }> = {
  sesion: { label: 'Sesión formativa', dot: 'bg-blue', chip: 'bg-sky-50 text-sky-900 border-sky-200' },
  entrega: { label: 'Entrega de proyecto', dot: 'bg-rose-500', chip: 'bg-rose-50 text-rose-900 border-rose-200' },
  taller: { label: 'Taller', dot: 'bg-teal', chip: 'bg-teal-50 text-teal-900 border-teal-200' },
  tutoria: { label: 'Tutoría', dot: 'bg-violet-500', chip: 'bg-violet-50 text-violet-900 border-violet-200' },
  revision: { label: 'Revisión / evaluación', dot: 'bg-amber-500', chip: 'bg-amber-50 text-amber-900 border-amber-200' },
  jornada: { label: 'Jornada informativa', dot: 'bg-gold', chip: 'bg-[#fff6df] text-[#6d5014] border-[#f3dca2]' },
  hito: { label: 'Hito administrativo', dot: 'bg-slate-500', chip: 'bg-slate-100 text-slate-800 border-slate-200' },
}

export function calendarItems(d: GistarData): CalItem[] {
  const evs: CalItem[] = d.eventos.map((e) => ({ ...e, evento: e }))
  const tasks: CalItem[] = d.tareas.map((t) => ({
    id: `TASK:${t.id}`,
    titulo: `Entrega · ${t.nombre}`,
    tipo: 'entrega',
    inicio: t.fecha_entrega,
    fin: t.fecha_entrega,
    cohorte_id: t.cohorte_id,
    responsable: cohortOf(d, t.cohorte_id)?.docente_responsable ?? DEMO_USER.docente,
    visibilidad: ['admin', 'docente', 'coder', 'coordinacion'],
    estado: t.estado === 'cancelada' ? 'cancelado' : 'programado',
    descripcion: t.descripcion,
    tarea_id: t.id,
  }))
  return [...evs, ...tasks].sort((a, b) => a.inicio.localeCompare(b.inicio))
}

export function canSeeItem(d: GistarData, role: Role, it: CalItem) {
  if (role === 'admin') return true
  if (role === 'docente') return !it.cohorte_id || nominalCohorts(d, role).some((c) => c.id === it.cohorte_id) || it.visibilidad.includes('docente')
  if (!it.visibilidad.includes(role)) return false
  if (role === 'coder') {
    const own = d.coders.find((c) => c.id === CODER_ID)!
    if (it.cohorte_id && it.cohorte_id !== own.cohorte_id) return false
    if (it.evento?.participante_id && it.evento.participante_id !== CODER_ID) return false
    return true
  }
  if (role === 'aspirante') return !it.evento?.participante_id || it.evento.participante_id === ASPIRANT_ID
  // Coordination and other internal roles: no individual appointments.
  return !it.evento?.participante_id
}
export function canEditItem(d: GistarData, role: Role, it: CalItem) {
  if (role === 'admin') return true
  if (role === 'docente') return !it.cohorte_id || nominalCohorts(d, role).some((c) => c.id === it.cohorte_id)
  return false
}

export function weekRange(today: string) {
  const from = weekStart(today)
  return { from, to: addDays(from, 6) }
}
