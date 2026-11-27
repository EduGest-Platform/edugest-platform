import {
  BarChart3,
  BookOpen,
  CalendarDays,
  CalendarRange,
  ClipboardList,
  IdCard,
  ClipboardCheck,
  FileStack,
  GraduationCap,
  Home,
  LayoutGrid,
  LifeBuoy,
  ListChecks,
  MessageSquareText,
  PenLine,
  ScrollText,
  TrendingUp,
  Users,
  UserRoundCheck,
  type LucideIcon,
} from 'lucide-react'
import type { Role, View } from './types'

export const ROLES: Record<Role, string> = {
  admin: 'Administración',
  docente: 'Docente',
  coder: 'Coder / alumnado',
  aspirante: 'Aspirante',
  fundacion: 'Personal fundación',
  seleccion: 'Selección',
  coordinacion: 'Coordinación',
}

export const MENUS: Record<Role, View[]> = {
  admin: ['dashboard', 'eventos', 'calendario', 'programas', 'competencias', 'rubricas', 'auditoria'],
  docente: ['dashboard', 'cohortes', 'analitica', 'eventos', 'calendario', 'alumnado', 'competencias', 'rubricas', 'entregas', 'asistencia', 'alertas', 'candidaturas', 'asistente'],
  coder: ['dashboard', 'eventos', 'calendario', 'progreso', 'entregas', 'asistente'],
  aspirante: ['dashboard', 'eventos', 'calendario', 'inscripcion', 'candidatura'],
  fundacion: ['dashboard', 'eventos', 'calendario', 'candidaturas', 'alertas'],
  seleccion: ['dashboard', 'eventos', 'calendario', 'candidaturas'],
  coordinacion: ['dashboard', 'eventos', 'calendario', 'cohortes'],
}

/** Views reachable by drill-down but not listed in the menu. */
export const EXTRA_VIEWS: Partial<Record<Role, View[]>> = { docente: ['ficha'] }
/** Views a role only has with the server, because they show real server data and the local demo has none for it. */
const API_ONLY_VIEWS: Partial<Record<Role, View[]>> = {
  coder: ['candidatura'],
  // KAN-275 (PO 27/11/2026): administration registers applications from the screen too.
  admin: ['candidaturas'],
}

export const menuFor = (role: Role, apiMode: boolean): View[] =>
  apiMode ? [...MENUS[role], ...(API_ONLY_VIEWS[role] ?? [])] : MENUS[role]

export const canOpen = (role: Role, v: View, apiMode = false) =>
  menuFor(role, apiMode).includes(v) || !!EXTRA_VIEWS[role]?.includes(v)

export const VIEWS: Record<View, { label: string; icon: LucideIcon }> = {
  dashboard: { label: 'Inicio', icon: Home },
  analitica: { label: 'Analítica del grupo', icon: BarChart3 },
  calendario: { label: 'Calendario', icon: CalendarDays },
  eventos: { label: 'Eventos', icon: CalendarRange },
  rubricas: { label: 'Rúbricas', icon: ClipboardList },
  ficha: { label: 'Ficha del coder', icon: IdCard },
  programas: { label: 'Programas', icon: LayoutGrid },
  competencias: { label: 'Competencias', icon: ListChecks },
  auditoria: { label: 'Auditoría', icon: ScrollText },
  alumnado: { label: 'Alumnado', icon: Users },
  asistencia: { label: 'Asistencia', icon: ClipboardCheck },
  entregas: { label: 'Entregas', icon: FileStack },
  alertas: { label: 'Tutoría y alertas', icon: LifeBuoy },
  asistente: { label: 'Asistente EduGest', icon: MessageSquareText },
  progreso: { label: 'Mi progreso', icon: TrendingUp },
  inscripcion: { label: 'Inscripción', icon: PenLine },
  candidatura: { label: 'Mi candidatura', icon: UserRoundCheck },
  candidaturas: { label: 'Candidaturas', icon: GraduationCap },
  cohortes: { label: 'Cohortes', icon: BookOpen },
}

export const APP_STATES = [
  'borrador',
  'enviada',
  'requisitos_en_revision',
  'convocada',
  'evaluacion_en_curso',
  'pendiente_decision_humana',
] as const

export const FINAL_STATES = ['admitida', 'lista_espera', 'no_admitida'] as const

export { ASPIRANT_ID, CODER_ID } from './domain'

export const humanize = (s: string | null | undefined) => (s || 'pendiente').replace(/_/g, ' ')
