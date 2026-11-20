import type { RequirementCheck } from '../requirements'

/**
 * Synthetic examples for the local prototype only (no server).
 * They let the team see every review state on the dossier until the API sends real reviews (KAN-128).
 * Never shown in API mode. All people and notes are invented.
 */

const AGE = 'Edad mínima de la convocatoria'
const AREA = 'Residencia en la zona del proyecto'
const UNEMPLOYED = 'Situación de desempleo'
const SKILLS = 'Conocimientos previos o competencias digitales'

const req = (id: string, label: string, kind: RequirementCheck['kind'], status: RequirementCheck['status'], note: string | null = null): RequirementCheck => ({
  id,
  label,
  kind,
  status,
  note,
  reviewedBy: status === 'pendiente' ? null : 'Selección (demo)',
  reviewedAt: status === 'pendiente' ? null : '2026-11-16',
})

export const REQUIREMENT_EXAMPLES: Record<string, RequirementCheck[]> = {
  // In review: some items are still pending.
  'A-003': [req('age', AGE, 'obligatorio', 'cumple'), req('area', AREA, 'obligatorio', 'pendiente'), req('job', UNEMPLOYED, 'obligatorio', 'pendiente'), req('skills', SKILLS, 'recomendado', 'pendiente')],
  // A required item is not met: the team must decide, nobody is excluded automatically.
  'A-012': [
    req('age', AGE, 'obligatorio', 'cumple'),
    req('area', AREA, 'obligatorio', 'no_cumple', 'Indica una residencia fuera de la zona. El equipo estudiará el caso.'),
    req('job', UNEMPLOYED, 'obligatorio', 'cumple'),
    req('skills', SKILLS, 'recomendado', 'pendiente'),
  ],
  // An exception is being studied.
  'A-005': [
    req('age', AGE, 'obligatorio', 'cumple'),
    req('area', AREA, 'obligatorio', 'cumple'),
    req('job', UNEMPLOYED, 'obligatorio', 'excepcion_en_revision', 'Se consulta con la entidad financiadora si el caso se puede justificar.'),
    req('skills', SKILLS, 'recomendado', 'cumple'),
  ],
  // Everything reviewed, with one approved exception.
  'A-006': [
    req('age', AGE, 'obligatorio', 'cumple'),
    req('area', AREA, 'obligatorio', 'cumple'),
    req('job', UNEMPLOYED, 'obligatorio', 'excepcion_aprobada', 'Excepción aprobada por el equipo y justificada ante la entidad financiadora.'),
    req('skills', SKILLS, 'recomendado', 'no_cumple'),
  ],
  'A-014': [req('age', AGE, 'obligatorio', 'cumple'), req('area', AREA, 'obligatorio', 'cumple'), req('job', UNEMPLOYED, 'obligatorio', 'cumple'), req('skills', SKILLS, 'recomendado', 'cumple')],
}
