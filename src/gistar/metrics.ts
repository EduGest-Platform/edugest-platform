import { attendanceSummary } from './domain'
import type { GistarData } from './types'

/** Aggregated (non-nominal) KPIs, computed from dated records. */
export function metrics(data: GistarData) {
  const att = data.cohortes.map((c) => attendanceSummary(data, c.id))
  const ok = att.reduce((a, s) => a + s.presente + s.retraso, 0)
  const reg = att.reduce((a, s) => a + s.registrados, 0)
  return {
    coders: data.coders.filter((c) => c.estado === 'activo').length,
    candidaturas: data.candidaturas.length,
    asistencia: reg ? Math.round((100 * ok) / reg) : null,
    asistenciaDen: reg,
    alertas: data.alertas_simuladas.filter((x) => x.estado === 'por_revisar').length,
  }
}
