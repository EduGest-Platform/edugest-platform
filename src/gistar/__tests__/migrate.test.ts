/* eslint-disable @typescript-eslint/no-explicit-any */
import { describe, expect, it } from 'vitest'
import seedV1 from '../seed.json'
import { migrate } from '../migrate'
import { attendanceSummary, effectiveCompetencies, latestEval } from '../domain'

describe('migration v1 → v2', () => {
  const d = migrate(structuredClone(seedV1))
  it('creates one historical evaluation per legacy non-null level', () => {
    const legacy = (seedV1 as any).evaluaciones_competencia.filter((e: any) => e.nivel_validado)
    expect(d.evaluaciones.filter((e) => e.origen === 'heredado_v1')).toHaveLength(legacy.length)
    expect(d.legacy_v1?.evaluaciones_competencia).toHaveLength(182)
  })
  it('derives current level from latest published evaluation, never level 0', () => {
    const legacy = (seedV1 as any).evaluaciones_competencia
    for (const x of legacy) {
      const e = latestEval(d.evaluaciones, x.coder_id, x.competencia_id, '2026-11-02')
      expect(e?.nivel ?? null).toBe(x.nivel_validado)
    }
  })
  it('rebuilds attendance from counters with identical totals', () => {
    for (const s of (seedV1 as any).asistencias_resumen) {
      const coh = d.coders.find((c) => c.id === s.coder_id)!.cohorte_id
      const a = attendanceSummary(d, coh, { coderId: s.coder_id })
      expect(a.presente).toBe(s.presencias)
      expect(a.ausente).toBe(s.faltas)
    }
  })
  it('keeps catalogs per program', () => {
    expect(effectiveCompetencies(d, 'COH-IA')).toHaveLength(10)
    expect(effectiveCompetencies(d, 'COH-DATA')).toHaveLength(8)
  })
  it('is idempotent on v2 data', () => {
    expect(migrate(structuredClone(d))).toEqual(d)
  })
})

describe('migration of user-modified v1 data', () => {
  it('preserves user changes from the previous app version', () => {
    const v1: any = structuredClone(seedV1)
    const a = v1.asistencias_resumen.find((x: any) => x.coder_id === 'E-003')
    a.sesiones_totales = 13
    a.faltas = 3
    v1.entregas.find((e: any) => e.id === 'ENT-001').estado = 'entregada'
    v1.competencias.push({ id: 'IA-11', programa_id: 'P-IA', codigo: 'C11', nombre: 'Automatización de flujos', niveles: { 1: 'x', 2: 'y', 3: 'z' }, activo: true })
    v1.candidaturas[0].estado = 'enviada'
    const d = migrate(v1)
    const s = attendanceSummary(d, 'COH-IA', { coderId: 'E-003' })
    expect([s.presente, s.ausente]).toEqual([10, 3])
    expect(d.entregas.find((e) => e.id === 'ENT-001')!.enviada_en).not.toBeNull()
    expect(effectiveCompetencies(d, 'COH-IA').map((c) => c.codigo)).toContain('C11')
    expect(d.candidaturas[0].estado).toBe('enviada')
  })
})
