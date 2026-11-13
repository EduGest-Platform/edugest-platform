export type Role = 'admin' | 'docente' | 'coder' | 'aspirante' | 'fundacion' | 'seleccion' | 'coordinacion'

export type View =
  | 'dashboard'
  | 'analitica'
  | 'calendario'
  | 'programas'
  | 'competencias'
  | 'rubricas'
  | 'auditoria'
  | 'alumnado'
  | 'ficha'
  | 'asistencia'
  | 'entregas'
  | 'alertas'
  | 'asistente'
  | 'progreso'
  | 'inscripcion'
  | 'candidatura'
  | 'candidaturas'
  | 'cohortes'

export type Level = 1 | 2 | 3

export interface Programa {
  id: string
  nombre: string
  descripcion: string
  cohorte_principal: string
}
export interface Cohorte {
  id: string
  programa_id: string
  nombre: string
  inicio: string
  fin: string
  docente_responsable: string
  /** Program-level competencies hidden for this cohort (cohort customisation). */
  competencias_excluidas: string[]
}
export interface Competencia {
  id: string
  programa_id: string
  /** null = program catalog (inherited by every cohort); otherwise cohort-specific. */
  cohorte_id: string | null
  codigo: string
  nombre: string
  descripcion: string
  niveles: Record<'1' | '2' | '3', string>
  activo: boolean
  orden: number
}
export interface Coder {
  id: string
  nombre_ficticio: string
  cohorte_id: string
  estado: string
  email_demo: string
}
export interface Validacion {
  resultado: string
  fecha: string
}
export interface Candidatura {
  id: string
  nombre_ficticio: string
  programa_id: string
  email_demo: string
  motivacion: string
  disponibilidad?: string
  estado: string
  asistencia_jornada: string
  ejercicio_acceso: string
  taller_recomendado: string
  entrevista: string
  recomendacion_preliminar: string | null
  validacion_docente: Validacion | null
  validacion_fundacion: Validacion | null
  decision_final: string | null
  requiere_contacto_confidencial: boolean
}

export interface Criterio {
  id: string
  nombre: string
  definicion: string
  evidencia: string
  peso: number | null
  competencias: string[]
}
export type RubricaEstado = 'borrador' | 'publicada' | 'archivada'
export interface Rubrica {
  id: string
  /** Groups all versions of the same rubric. */
  familia_id: string
  tarea_id: string
  nombre: string
  version: number
  estado: RubricaEstado
  criterios: Criterio[]
  creada_en: string
  publicada_en: string | null
  basada_en: string | null
}
export interface Tarea {
  id: string
  programa_id: string
  cohorte_id: string
  nombre: string
  descripcion: string
  /** Single source of truth for the deadline shown in calendar and deliveries. YYYY-MM-DDTHH:mm Europe/Madrid */
  fecha_entrega: string
  /** Currently published rubric version used for new reviews. */
  rubrica_id: string | null
  estado: 'activa' | 'cancelada'
}
export interface Entrega {
  id: string
  coder_id: string
  tarea_id: string
  /** Legacy v1 status, kept for traceability only. */
  estado: string
  enviada_en: string | null
  repositorio_ficticio: string
  feedback_borrador: string | null
  feedback_publicado: string | null
  nota_migracion?: string
}
export interface RevisionCriterio {
  criterio_id: string
  nivel: Level | null
  evidencia: string
  comentario: string
}
export interface Revision {
  id: string
  entrega_id: string
  rubrica_id: string
  rubrica_version: number
  evaluador: string
  estado: 'borrador' | 'publicada'
  creada_en: string
  publicada_en: string | null
  criterios: RevisionCriterio[]
  competencias: { competencia_id: string; nivel: Level | null }[]
  feedback: string
  origen?: 'heredado_v1' | 'sintetico_seed' | 'demo'
}
export type EvalOrigen = 'heredado_v1' | 'sintetico_seed' | 'demo'
export interface Evaluacion {
  id: string
  coder_id: string
  competencia_id: string
  tarea_id: string | null
  entrega_id: string | null
  revision_id: string | null
  rubrica_id: string | null
  rubrica_version: number | null
  evaluador: string
  nivel: Level
  evidencia: string
  comentario: string
  estado: 'borrador' | 'publicada'
  /** YYYY-MM-DD */
  fecha: string
  origen: EvalOrigen
  seq: number
}

export type EventType = 'sesion' | 'entrega' | 'taller' | 'tutoria' | 'revision' | 'jornada' | 'hito'
export interface Evento {
  id: string
  titulo: string
  tipo: Exclude<EventType, 'entrega'>
  /** YYYY-MM-DDTHH:mm wall time in `zona` */
  inicio: string
  fin: string
  zona: 'Europe/Madrid'
  cohorte_id: string | null
  responsable: string
  visibilidad: Role[]
  estado: 'programado' | 'cancelado'
  descripcion: string
  participante_id?: string | null
  origen?: 'heredado_v1' | 'sintetico_seed' | 'demo'
}
/** Calendar item: stored event or a delivery deadline derived from a Tarea. */
export interface CalItem {
  id: string
  titulo: string
  tipo: EventType
  inicio: string
  fin: string
  cohorte_id: string | null
  responsable: string
  visibilidad: Role[]
  estado: 'programado' | 'cancelado'
  descripcion: string
  tarea_id?: string
  evento?: Evento
}

export type AsistEstado = 'presente' | 'ausente' | 'retraso' | 'pendiente'
export interface RegistroAsistencia {
  id: string
  evento_id: string
  coder_id: string
  estado: AsistEstado
  comentario: string
  actualizado_en: string
  historial: { en: string; estado: AsistEstado; actor: string; comentario: string }[]
  origen: 'heredado_v1' | 'demo'
}

export interface Alerta {
  id: string
  coder_id: string
  estado: string
  senales: string[]
  explicacion?: string
  creada_en?: string
  plan_apoyo: string | null
  es_prediccion_real: boolean
}
export interface PlanApoyo {
  alerta_id: string
  coder_id: string
  nota: string
  responsable: string
  fecha_revision: string
}
export interface Documento {
  id: string
  programa_id: string
  titulo: string
  secciones: { id: string; titulo: string; contenido: string }[]
}
export interface RespuestaRag {
  clave: string
  pregunta: string
  respuesta: string
  doc_id: string
  seccion_id: string
}
export interface Bitacora {
  id: string
  fecha_simulada: string
  actor_rol: string
  entidad: string
  accion: string
  detalle: string
}

export interface GistarData {
  schema_version: 2
  meta: { fecha_simulada: string; nota: string; migrado_desde?: string; [k: string]: unknown }
  usuarios_demo: { id: string; rol: Role; nombre: string; entidad_demo_id: string | null }[]
  programas: Programa[]
  cohortes: Cohorte[]
  competencias: Competencia[]
  coders: Coder[]
  candidaturas: Candidatura[]
  formulario_demo: unknown
  tareas: Tarea[]
  rubricas: Rubrica[]
  entregas: Entrega[]
  revisiones: Revision[]
  evaluaciones: Evaluacion[]
  eventos: Evento[]
  asistencia: RegistroAsistencia[]
  alertas_simuladas: Alerta[]
  planes_apoyo: PlanApoyo[]
  documentos: Documento[]
  respuestas_rag_mock: RespuestaRag[]
  bitacora_demo: Bitacora[]
  escenarios_prueba: Record<string, string>
  /** Raw v1 structures preserved after migration (read-only, for traceability). */
  legacy_v1?: { evaluaciones_competencia?: unknown[]; asistencias_resumen?: unknown[] }
}
