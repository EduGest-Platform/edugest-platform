/* eslint-disable @typescript-eslint/no-explicit-any */
import { addDays, dayOf, weekday } from './dates'
import type { Criterio, Evaluacion, Evento, GistarData, Level, RegistroAsistencia, Revision, Rubrica, Tarea } from './types'

/**
 * Schema migration gistar-demo-v1 → v2.
 * - nivel_validado (overwritten value) → dated, historical evaluations. Legacy values become a single
 *   initial point flagged `heredado_v1` on a synthetic cut-off date (no real dates are invented).
 * - asistencias_resumen counters → one attendance record per coder and dated session.
 * - tareas get a cohort, a full deadline and a versioned rubric; calendar deadlines are derived from them.
 * Raw v1 structures are preserved under `legacy_v1`.
 */
export const LEGACY_CUTOFF = '2026-10-30'
const HOLIDAYS = new Set(['2026-10-12', '2026-11-01', '2026-12-08'])

const CRITERIA_MAP: Record<string, Record<string, string[]>> = {
  'T-IA-01': { 'solución': ['IA-01', 'IA-04'], pruebas: ['IA-02'], 'documentación': ['IA-09'] },
  'T-DAT-01': { datos: ['DAT-01', 'DAT-07'], 'visualización': ['DAT-04'], 'explicación': ['DAT-08'] },
}
const SESSION_PLAN: Record<string, { days: number[]; start: string; end: string; label: string }> = {
  'COH-IA': { days: [0, 3], start: '09:30', end: '13:30', label: 'IA aplicada' },
  'COH-DATA': { days: [1, 4], start: '15:30', end: '19:30', label: 'Data y automatización' },
}

const ALL_INTERNAL = ['admin', 'docente', 'coder', 'coordinacion'] as const

function sessionDates(from: string, to: string, days: number[]) {
  const out: string[] = []
  for (let d = from; d <= to; d = addDays(d, 1)) if (days.includes(weekday(d)) && !HOLIDAYS.has(d)) out.push(d)
  return out
}

export function migrate(raw: any): GistarData {
  if (raw?.schema_version === 2) return ensureV2(raw)
  const v1 = structuredClone(raw)
  const d: any = structuredClone(raw)
  const today: string = d.meta?.fecha_simulada ?? '2026-11-02'
  const now = `${today}T12:00`
  let seq = 1

  // Cohorts & competencies
  for (const c of d.cohortes) c.competencias_excluidas ??= []
  const order: Record<string, number> = {}
  d.competencias = d.competencias.map((c: any) => {
    order[c.programa_id] = (order[c.programa_id] ?? 0) + 1
    return {
      id: c.id,
      programa_id: c.programa_id,
      cohorte_id: c.cohorte_id ?? null,
      codigo: c.codigo,
      nombre: c.nombre,
      descripcion: c.descripcion ?? `Competencia «${c.nombre}» del catálogo del programa (descripción sintética).`,
      niveles: { '1': c.niveles?.['1'] ?? c.niveles?.[1] ?? '', '2': c.niveles?.['2'] ?? c.niveles?.[2] ?? '', '3': c.niveles?.['3'] ?? c.niveles?.[3] ?? '' },
      activo: c.activo ?? true,
      orden: c.orden ?? order[c.programa_id],
    }
  })
  const cohortForProgram = (p: string) => d.cohortes.find((c: any) => c.programa_id === p)?.id

  // Tasks + rubrics
  const rubricas: Rubrica[] = []
  const tareas: Tarea[] = (d.tareas ?? []).map((t: any) => {
    const cohorte_id = t.cohorte_id ?? cohortForProgram(t.programa_id)
    const rid = `RUB-${t.id}-v1`
    const criterios: Criterio[] = (t.rubrica ?? []).map((name: string, i: number) => ({
      id: `${rid}-K${i + 1}`,
      nombre: name.charAt(0).toUpperCase() + name.slice(1),
      definicion: `Criterio heredado del modelo v1 («${name}»).`,
      evidencia: 'Repositorio ficticio y memoria de la entrega.',
      peso: null,
      competencias: CRITERIA_MAP[t.id]?.[name] ?? [],
    }))
    rubricas.push({
      id: rid,
      familia_id: `RF-${t.id}`,
      tarea_id: t.id,
      nombre: `Rúbrica ${t.nombre}`,
      version: 1,
      estado: 'publicada',
      criterios,
      creada_en: d.cohortes.find((c: any) => c.id === cohorte_id)?.inicio ?? today,
      publicada_en: d.cohortes.find((c: any) => c.id === cohorte_id)?.inicio ?? today,
      basada_en: null,
    })
    return {
      id: t.id,
      programa_id: t.programa_id,
      cohorte_id,
      nombre: t.nombre,
      descripcion: t.descripcion ?? `Rúbrica: ${(t.rubrica ?? []).join(', ')}`,
      fecha_entrega: t.fecha_entrega.length === 10 ? `${t.fecha_entrega}T23:59` : t.fecha_entrega,
      rubrica_id: rid,
      estado: 'activa',
    }
  })

  // Legacy entregas
  const revisiones: Revision[] = []
  d.entregas = (d.entregas ?? []).map((e: any) => {
    const n: any = { ...e, enviada_en: e.enviada_en ?? null }
    if (e.enviada_en === undefined) {
      if (e.estado === 'enviada') n.enviada_en = `${LEGACY_CUTOFF}T18:00`
      else if (e.estado === 'entregada') n.enviada_en = `${today}T10:00`
      else if (e.estado === 'fuera_de_plazo') n.nota_migracion = 'En v1 figuraba «fuera de plazo» antes de vencer el plazo; se migra como pendiente.'
    }
    if (e.feedback_publicado && n.enviada_en) {
      const t = tareas.find((x) => x.id === e.tarea_id)
      revisiones.push({
        id: `REV-H-${e.id}`,
        entrega_id: e.id,
        rubrica_id: t?.rubrica_id ?? '',
        rubrica_version: 1,
        evaluador: 'USR-DOC',
        estado: 'publicada',
        creada_en: LEGACY_CUTOFF,
        publicada_en: LEGACY_CUTOFF,
        criterios: [],
        competencias: [],
        feedback: e.feedback_publicado,
        origen: 'heredado_v1',
      })
    }
    return n
  })

  // Historical evaluations from nivel_validado
  const legacyEvals: any[] = d.evaluaciones_competencia ?? []
  const legacyLevel = (coder: string, comp: string): Level | null =>
    legacyEvals.find((x) => x.coder_id === coder && x.competencia_id === comp)?.nivel_validado ?? null
  const evaluaciones: Evaluacion[] = []

  // Synthetic sprint 1 (past task) to give the demo a dated trajectory before the legacy cut-off.
  const sprints = [
    {
      id: 'T-IA-00', cohort: 'COH-IA', programa: 'P-IA', nombre: 'Sprint 1 · Fundamentos de programación', deadline: '2026-10-16T23:59', reviewed: '2026-10-20',
      criterios: [
        ['Código funcional', 'El programa resuelve el enunciado con entradas válidas.', 'Ejecución en repositorio ficticio', 50, ['IA-01']],
        ['Uso de control de versiones', 'Commits frecuentes y descriptivos.', 'Historial de commits', 30, ['IA-03']],
        ['Trabajo en pareja', 'Reparte tareas y documenta acuerdos.', 'Notas de la retrospectiva', 20, ['IA-07']],
      ],
    },
    {
      id: 'T-DAT-00', cohort: 'COH-DATA', programa: 'P-DATA', nombre: 'Sprint 1 · Consultas y limpieza', deadline: '2026-10-23T23:59', reviewed: '2026-10-27',
      criterios: [
        ['Consultas SQL', 'Consultas correctas y legibles.', 'Script SQL', 50, ['DAT-02']],
        ['Limpieza de datos', 'Detecta y trata valores anómalos.', 'Cuaderno de limpieza', 50, ['DAT-03', 'DAT-07']],
      ],
    },
  ] as const
  const late = new Set(['E-005', 'E-009', 'E-015'])
  const missing = new Set(['E-019'])
  const unreviewed = new Set(['E-002', 'E-006', 'E-013', 'E-017'])
  for (const sp of sprints) {
    if (tareas.some((t) => t.id === sp.id) || !d.cohortes.some((c: any) => c.id === sp.cohort)) continue
    const rid = `RUB-${sp.id}-v1`
    const criterios: Criterio[] = sp.criterios.map(([nombre, definicion, evidencia, peso, comps], i) => ({
      id: `${rid}-K${i + 1}`, nombre, definicion, evidencia, peso, competencias: [...comps],
    }))
    rubricas.push({ id: rid, familia_id: `RF-${sp.id}`, tarea_id: sp.id, nombre: `Rúbrica ${sp.nombre}`, version: 1, estado: 'publicada', criterios, creada_en: '2026-10-01', publicada_en: '2026-10-01', basada_en: null })
    tareas.unshift({ id: sp.id, programa_id: sp.programa, cohorte_id: sp.cohort, nombre: sp.nombre, descripcion: 'Tarea sintética añadida en la migración v2 para disponer de historial fechado.', fecha_entrega: sp.deadline, rubrica_id: rid, estado: 'activa' })
    for (const c of d.coders.filter((x: any) => x.cohorte_id === sp.cohort)) {
      const eid = `ENT-${sp.id}-${c.id}`
      const deadlineDay = dayOf(sp.deadline)
      const enviada_en = missing.has(c.id) ? null : late.has(c.id) ? `${addDays(deadlineDay, 2)}T10:00` : `${addDays(deadlineDay, -1)}T20:00`
      d.entregas.push({ id: eid, coder_id: c.id, tarea_id: sp.id, estado: enviada_en ? 'enviada' : 'pendiente', enviada_en, repositorio_ficticio: `https://example.test/repos/${c.id.toLowerCase()}-sprint1`, feedback_borrador: null, feedback_publicado: null })
      if (!enviada_en || unreviewed.has(c.id)) continue
      const compLevels = criterios.flatMap((k) => k.competencias).map((comp) => {
        const L = legacyLevel(c.id, comp)
        return { competencia_id: comp, nivel: L === null ? null : ((L >= 2 ? L - 1 : 1) as Level) }
      })
      if (compLevels.every((x) => x.nivel === null)) continue
      const revId = `REV-S-${eid}`
      const feedback = 'Feedback sintético del sprint 1: buen punto de partida; consolidar la documentación de decisiones.'
      revisiones.push({
        id: revId, entrega_id: eid, rubrica_id: rid, rubrica_version: 1, evaluador: 'USR-DOC', estado: 'publicada', creada_en: sp.reviewed, publicada_en: sp.reviewed,
        criterios: criterios.map((k) => {
          const lv = compLevels.filter((x) => k.competencias.includes(x.competencia_id) && x.nivel).map((x) => x.nivel as number)
          return { criterio_id: k.id, nivel: lv.length ? (Math.min(...lv) as Level) : null, evidencia: k.evidencia, comentario: '' }
        }),
        competencias: compLevels, feedback, origen: 'sintetico_seed',
      })
      const ent = d.entregas[d.entregas.length - 1]
      ent.feedback_publicado = feedback
      for (const cl of compLevels) {
        if (!cl.nivel) continue
        evaluaciones.push({
          id: `EVA-${revId}-${cl.competencia_id}`, coder_id: c.id, competencia_id: cl.competencia_id, tarea_id: sp.id, entrega_id: eid, revision_id: revId,
          rubrica_id: rid, rubrica_version: 1, evaluador: 'USR-DOC', nivel: cl.nivel, evidencia: 'Revisión sintética del sprint 1', comentario: '',
          estado: 'publicada', fecha: sp.reviewed, origen: 'sintetico_seed', seq: seq++,
        })
      }
    }
  }
  for (const x of legacyEvals) {
    if (!x.nivel_validado) continue
    evaluaciones.push({
      id: `EVA-H-${x.coder_id}-${x.competencia_id}`, coder_id: x.coder_id, competencia_id: x.competencia_id, tarea_id: null, entrega_id: null, revision_id: null,
      rubrica_id: null, rubrica_version: null, evaluador: 'USR-DOC', nivel: x.nivel_validado, evidencia: 'Valor heredado del modelo v1 (sin fecha original).',
      comentario: 'Punto inicial heredado · fecha de corte sintética', estado: 'publicada', fecha: LEGACY_CUTOFF, origen: 'heredado_v1', seq: seq++,
    })
  }

  // Sessions + attendance records from counters
  const eventos: Evento[] = []
  const asistencia: RegistroAsistencia[] = []
  const summaries: any[] = d.asistencias_resumen ?? []
  for (const coh of d.cohortes) {
    const plan = SESSION_PLAN[coh.id] ?? { days: [0, 2], start: '10:00', end: '14:00', label: coh.nombre }
    const dates = sessionDates(coh.inicio, coh.fin, plan.days)
    dates.forEach((day, i) =>
      eventos.push({
        id: `SES-${coh.id}-${String(i + 1).padStart(2, '0')}`, titulo: `Sesión ${i + 1} · ${plan.label}`, tipo: 'sesion',
        inicio: `${day}T${plan.start}`, fin: `${day}T${plan.end}`, zona: 'Europe/Madrid', cohorte_id: coh.id, responsable: coh.docente_responsable,
        visibilidad: [...ALL_INTERNAL], estado: 'programado', descripcion: 'Sesión presencial del programa.', origen: 'sintetico_seed',
      }),
    )
    const past = eventos.filter((e) => e.cohorte_id === coh.id && e.inicio <= now)
    const cohortSums = summaries.filter((s) => d.coders.find((c: any) => c.id === s.coder_id)?.cohorte_id === coh.id)
    const heredadas = Math.min(past.length, Math.max(0, ...cohortSums.map((s) => s.sesiones_totales)))
    for (const s of cohortSums) {
      const total = Math.min(s.sesiones_totales, heredadas)
      const absent = new Set<number>()
      for (let k = 0, idx = total - 1; k < Math.min(s.faltas, total); k++, idx -= 2) absent.add(idx >= 0 ? idx : total - 1 - k)
      for (let i = 0; i < total; i++) {
        const est = absent.has(i) ? 'ausente' : 'presente'
        asistencia.push({
          id: `ATT-${past[i].id}-${s.coder_id}`, evento_id: past[i].id, coder_id: s.coder_id, estado: est, comentario: '',
          actualizado_en: dayOf(past[i].inicio), historial: [{ en: dayOf(past[i].inicio), estado: est, actor: 'migración v1', comentario: 'Registro reconstruido desde contadores v1' }], origen: 'heredado_v1',
        })
      }
    }
  }
  const extra: [string, Evento['tipo'], string, string, string | null, Evento['visibilidad'], string, string?][] = [
    ['Taller · Automatización con flujos', 'taller', '2026-11-03T16:00', '2026-11-03T18:00', 'COH-DATA', [...ALL_INTERNAL], 'Taller práctico opcional.'],
    ['Tutoría individual de seguimiento', 'tutoria', '2026-11-04T13:30', '2026-11-04T14:00', 'COH-IA', ['admin', 'docente', 'coder'], 'Tutoría de seguimiento acordada.', 'E-001'],
    ['Taller · Prompting responsable', 'taller', '2026-11-05T16:00', '2026-11-05T18:00', 'COH-IA', [...ALL_INTERNAL], 'Buenas prácticas y ética de uso.'],
    ['Jornada informativa y convocatoria de acceso', 'jornada', '2026-11-05T17:30', '2026-11-05T19:00', null, ['admin', 'docente', 'aspirante', 'fundacion', 'seleccion', 'coordinacion'], 'Presentación de los programas para aspirantes.'],
    ['Prueba de acceso · convocatoria noviembre', 'jornada', '2026-11-12T10:00', '2026-11-12T12:00', null, ['admin', 'docente', 'aspirante', 'fundacion', 'seleccion'], 'Ejercicio de acceso para candidaturas enviadas.'],
    ['Cierre de inscripciones', 'hito', '2026-11-15T23:59', '2026-11-15T23:59', null, ['admin', 'docente', 'coder', 'aspirante', 'fundacion', 'seleccion', 'coordinacion'], 'Fecha límite de la convocatoria.'],
    ['Revisión de portfolio', 'revision', '2026-11-19T10:00', '2026-11-19T13:00', 'COH-IA', [...ALL_INTERNAL], 'Revisión de portfolio (Roadmap IA aplicada, sección Calendario).'],
    ['Comité de admisión', 'hito', '2026-11-20T09:00', '2026-11-20T11:00', null, ['admin', 'docente', 'fundacion', 'seleccion', 'coordinacion'], 'Revisión humana de decisiones de admisión.'],
    ['Revisión de proyectos Data', 'revision', '2026-11-27T15:30', '2026-11-27T19:00', 'COH-DATA', [...ALL_INTERNAL], 'Presentación del dashboard final.'],
  ]
  extra.forEach(([titulo, tipo, inicio, fin, cohorte_id, visibilidad, descripcion, participante], i) =>
    eventos.push({ id: `EVT-${String(i + 1).padStart(2, '0')}`, titulo, tipo, inicio, fin, zona: 'Europe/Madrid', cohorte_id, responsable: 'USR-DOC', visibilidad, estado: 'programado', descripcion, participante_id: participante ?? null, origen: 'sintetico_seed' }),
  )

  for (const a of d.alertas_simuladas ?? [])
    a.explicacion ??= 'Señal ilustrativa heredada del modelo v1: combina ausencias y una entrega fuera de plazo. Requiere revisión humana.'

  const { evaluaciones_competencia: _e, asistencias_resumen: _a, ...rest } = d
  const out: GistarData = {
    ...rest,
    schema_version: 2,
    tareas,
    rubricas,
    revisiones,
    evaluaciones,
    eventos,
    asistencia,
    legacy_v1: { evaluaciones_competencia: v1.evaluaciones_competencia, asistencias_resumen: v1.asistencias_resumen },
  }
  out.bitacora_demo = [
    { id: 'EV-MIG-V2', fecha_simulada: today, actor_rol: 'sistema', entidad: 'esquema', accion: 'migracion_v1_v2', detalle: `${evaluaciones.length} evaluaciones históricas, ${asistencia.length} registros de asistencia` },
    ...(out.bitacora_demo ?? []),
  ]
  return ensureV2(out)
}

function ensureV2(d: any): GistarData {
  for (const k of ['tareas', 'rubricas', 'entregas', 'revisiones', 'evaluaciones', 'eventos', 'asistencia', 'alertas_simuladas', 'planes_apoyo', 'bitacora_demo', 'competencias', 'cohortes'])
    d[k] ??= []
  for (const c of d.cohortes) c.competencias_excluidas ??= []
  return d as GistarData
}
