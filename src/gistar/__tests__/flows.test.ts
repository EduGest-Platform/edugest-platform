import { beforeEach, describe, expect, it } from 'vitest'
import seedV1 from '../seed.json'
import { migrate } from '../migrate'
import { addCompetency, applyAttendance, applyReview, publishRubric, saveRubricDraft, validateRubric } from '../actions'
import { groupAnalytics } from '../analytics'
import { attendanceSummary, calendarItems, canSeeItem, effectiveCompetencies, latestEval, nominalCohorts, nowOf } from '../domain'
import { canOpen, MENUS } from '../config'
import type { GistarData } from '../types'

let d: GistarData
beforeEach(() => {
  d = migrate(structuredClone(seedV1))
})
const ga = (cohortId: string, extra: Partial<Parameters<typeof groupAnalytics>[1]> = {}) =>
  groupAnalytics(d, { cohortId, from: d.cohortes.find((c) => c.id === cohortId)!.inicio, to: d.meta.fecha_simulada, compIds: null, tareaId: null, ...extra })

describe('1 · cohort-scoped analytics', () => {
  it('changes N and competencies with the cohort', () => {
    const ia = ga('COH-IA')
    const data = ga('COH-DATA')
    expect(ia.coders.every((c) => c.cohorte_id === 'COH-IA')).toBe(true)
    expect([ia.coders.length, ia.comps.length]).toEqual([11, 10])
    expect([data.coders.length, data.comps.length]).toEqual([9, 8])
    expect(nominalCohorts(d, 'docente').map((c) => c.id)).toEqual(['COH-IA', 'COH-DATA'])
  })
})

describe('2 · open competency catalog', () => {
  it('adds C9 to Data without touching IA', () => {
    const before = effectiveCompetencies(d, 'COH-IA').map((c) => c.id)
    const c = addCompetency(d, 'P-DATA', null, { nombre: 'Orquestación', descripcion: '', niveles: { '1': 'a', '2': 'b', '3': 'c' } })
    expect(c.codigo).toBe('C9')
    const c2 = addCompetency(d, 'P-DATA', null, { nombre: 'APIs', descripcion: '', niveles: { '1': 'a', '2': 'b', '3': 'c' } })
    expect(c2.codigo).toBe('C10')
    expect(effectiveCompetencies(d, 'COH-DATA')).toHaveLength(10)
    expect(effectiveCompetencies(d, 'COH-IA').map((x) => x.id)).toEqual(before)
    expect(() => addCompetency(d, 'P-DATA', null, { nombre: 'sql', descripcion: '', niveles: { '1': '', '2': '', '3': '' } })).toThrow()
  })
})

describe('3/4 · rubric → review → draft → publish → history', () => {
  it('drafts do not change metrics; publishing does; old evaluation kept', () => {
    const crit = ['Diseño', 'Pruebas', 'Documentación', 'Ética'].map((n, i) => ({ id: `K${i}`, nombre: n, definicion: '', evidencia: '', peso: 25, competencias: [['IA-01'], ['IA-02'], ['IA-09'], ['IA-08']][i] }))
    expect(validateRubric(crit)).toBeNull()
    expect(validateRubric(crit.map((k) => ({ ...k, peso: 20 })))).toMatch(/100/)
    const r = saveRubricDraft(d, { tarea_id: 'T-IA-01', nombre: 'Rúbrica v2', criterios: crit, basada_en: null })
    publishRubric(d, r.id)
    expect(r.version).toBe(2)
    expect(d.rubricas.find((x) => x.id === 'RUB-T-IA-01-v1')!.estado).toBe('archivada')

    const coder = 'E-002'
    const ent = d.entregas.find((e) => e.coder_id === coder && e.tarea_id === 'T-IA-01')!
    const prev = latestEval(d.evaluaciones, coder, 'IA-08', d.meta.fecha_simulada)!
    const base = ga('COH-IA')
    const input = { entregaId: ent.id, rubricaId: r.id, criterios: Object.fromEntries(crit.map((k) => [k.id, { nivel: 3 as const, evidencia: 'ok', comentario: '' }])), competencias: ['IA-01', 'IA-02', 'IA-09', 'IA-08'].map((id) => ({ competencia_id: id, nivel: 3 as const })), feedback: 'Bien' }
    applyReview(d, { ...input, publish: false })
    const afterDraft = ga('COH-IA')
    expect(afterDraft.current).toEqual(base.current)
    expect(afterDraft.matrix.get(coder)!.get('IA-08')).toBe(prev.nivel)
    expect(d.entregas.find((e) => e.id === ent.id)!.feedback_publicado).not.toBe('Bien')

    applyReview(d, { ...input, publish: true })
    const afterPub = ga('COH-IA')
    expect(afterPub.matrix.get(coder)!.get('IA-08')).toBe(3)
    expect(afterPub.evo[afterPub.evo.length - 1].mastered).toBeGreaterThanOrEqual(base.evo[base.evo.length - 1].mastered)
    // history preserved
    const hist = d.evaluaciones.filter((e) => e.coder_id === coder && e.competencia_id === 'IA-08' && e.estado === 'publicada')
    expect(hist.map((h) => h.id)).toContain(prev.id)
    expect(hist.length).toBe(2)
    // no duplicated drafts left behind
    expect(d.evaluaciones.filter((e) => e.entrega_id === ent.id && e.estado === 'borrador')).toHaveLength(0)
  })
})

describe('5 · coder visibility', () => {
  it('coder calendar shows only own cohort items and own tutorials', () => {
    const items = calendarItems(d).filter((i) => canSeeItem(d, 'coder', i))
    expect(items.every((i) => !i.cohorte_id || i.cohorte_id === 'COH-IA')).toBe(true)
    expect(items.some((i) => i.tipo === 'entrega' && i.tarea_id === 'T-IA-01')).toBe(true)
    expect(canOpen('coder', 'analitica')).toBe(false)
    expect(canOpen('coder', 'ficha')).toBe(false)
  })
})

describe('6/7 · attendance per dated session', () => {
  it('records once, edits without duplicating, future sessions do not count', () => {
    const ses = { id: 'EVT-T1', titulo: 'Sesión extra', tipo: 'sesion' as const, inicio: `${d.meta.fecha_simulada}T08:00`, fin: `${d.meta.fecha_simulada}T10:00`, zona: 'Europe/Madrid' as const, cohorte_id: 'COH-DATA', responsable: 'USR-DOC', visibilidad: [], estado: 'programado' as const, descripcion: '' }
    d.eventos.push(ses)
    const g0 = attendanceSummary(d, 'COH-DATA')
    const s0 = attendanceSummary(d, 'COH-DATA', { coderId: 'E-012' })
    applyAttendance(d, ses.id, { 'E-012': { estado: 'presente', comentario: '' }, 'E-013': { estado: 'ausente', comentario: '' } })
    const g1 = attendanceSummary(d, 'COH-DATA')
    expect(g1.registrados).toBe(g0.registrados + 2)
    expect(g1.ausente).toBe(g0.ausente + 1)
    expect(attendanceSummary(d, 'COH-DATA', { coderId: 'E-012' }).presente).toBe(s0.presente + 1)
    applyAttendance(d, ses.id, { 'E-013': { estado: 'retraso', comentario: 'tren' } })
    const g2 = attendanceSummary(d, 'COH-DATA')
    expect(g2.registrados).toBe(g1.registrados)
    expect(d.asistencia.filter((r) => r.evento_id === ses.id && r.coder_id === 'E-013')).toHaveLength(1)
    expect(d.asistencia.find((r) => r.evento_id === ses.id && r.coder_id === 'E-013')!.historial).toHaveLength(2)
    // future sessions: none counted
    const future = d.eventos.filter((e) => e.tipo === 'sesion' && e.cohorte_id === 'COH-DATA' && e.inicio > nowOf(d)).length
    expect(future).toBeGreaterThan(0)
    expect(g2.celebradas).toBe(d.eventos.filter((e) => e.tipo === 'sesion' && e.cohorte_id === 'COH-DATA' && e.inicio <= nowOf(d)).length)
  })
  it('E-003 alert appears after the third confirmed absence', () => {
    const next = d.eventos.find((e) => e.cohorte_id === 'COH-IA' && e.tipo === 'sesion' && e.inicio <= nowOf(d) && !d.asistencia.some((r) => r.evento_id === e.id))!
    applyAttendance(d, next.id, { 'E-003': { estado: 'ausente', comentario: '' } })
    expect(d.alertas_simuladas.some((a) => a.coder_id === 'E-003' && a.estado === 'por_revisar')).toBe(true)
  })
  it('unevaluated competency is null, not 0', () => {
    const g = ga('COH-IA')
    expect(g.matrix.get('E-008')!.get('IA-01')).toBeNull()
  })
})

describe('8 · filters', () => {
  it('date and competency filters change n/N', () => {
    const all = ga('COH-IA')
    const early = ga('COH-IA', { to: '2026-10-25' })
    expect(early.current.evaluated).toBeLessThan(all.current.evaluated)
    const one = ga('COH-IA', { compIds: ['IA-01'] })
    expect(one.current.pairs).toBe(11)
    const empty = ga('COH-IA', { to: '2026-09-20' })
    expect(empty.current.evaluated).toBe(0)
    expect(empty.current.mastery).toBeNull()
  })
})

describe('9/10 · role access', () => {
  it('coordination has no nominal views', () => {
    for (const v of ['analitica', 'ficha', 'alumnado', 'entregas', 'asistencia'] as const) expect(canOpen('coordinacion', v)).toBe(false)
    expect(nominalCohorts(d, 'coordinacion')).toHaveLength(0)
    expect(canOpen('docente', 'analitica')).toBe(true)
    expect(canOpen('docente', 'ficha')).toBe(true)
  })
  it('every role has the calendar', () => {
    for (const r of Object.keys(MENUS) as (keyof typeof MENUS)[]) expect(MENUS[r]).toContain('calendario')
  })
})
