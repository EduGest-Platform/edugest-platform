import { CloudOff, LogOut, RotateCcw } from 'lucide-react'
import { useEffect, useMemo, type ReactElement } from 'react'
import { API_MODE, API_VIEWS } from '../shared/api/config'
import { uiRolesFor, useApiSession } from '../shared/api/session'
import { MENUS, ROLES, VIEWS } from './config'
import { useGistar } from './store'
import type { Role, View } from './types'
import { Button, inputCls } from './ui'
import { Dashboard } from './views/Dashboard'
import { Applications } from './views/Applications'
import { Inscription, MyApplication } from './views/Aspirant'
import { StudentList } from './views/Students'
import { Alerts, Attendance } from './views/FollowUp'
import { Deliveries } from './views/Deliveries'
import { CoderProfile } from './views/Profile'
import { CompetencyCatalog } from './views/Catalog'
import { Rubrics } from './views/Rubrics'
import { Calendar } from './views/Calendar'
import { GroupAnalytics } from './views/GroupAnalytics'
import { Assistant } from './views/Assistant'
import { AuditTrail, Coordination, Programs } from './views/Admin'
import { ApiApplications, ApiAudit, ApiInscription, ApiMyApplications } from './views/api/ApiAdmissions'
import { LoginScreen } from './components/LoginScreen'

const SCREENS: Record<View, () => ReactElement> = {
  dashboard: Dashboard,
  analitica: GroupAnalytics,
  calendario: Calendar,
  rubricas: Rubrics,
  ficha: CoderProfile,
  programas: Programs,
  competencias: CompetencyCatalog,
  auditoria: AuditTrail,
  alumnado: StudentList,
  asistencia: Attendance,
  entregas: Deliveries,
  alertas: Alerts,
  asistente: Assistant,
  progreso: CoderProfile,
  inscripcion: Inscription,
  candidatura: MyApplication,
  candidaturas: Applications,
  cohortes: Coordination,
}

/** In API mode these views read/write the FastAPI backend instead of localStorage. */
const API_SCREENS: Partial<Record<View, () => ReactElement>> = {
  inscripcion: ApiInscription,
  candidatura: ApiMyApplications,
  candidaturas: ApiApplications,
  auditoria: ApiAudit,
}

function Logo() {
  return (
    <div className="flex items-center gap-2.5 px-3 text-white">
      <span className="flex size-8 items-center justify-center rounded-lg bg-gold text-navy">
        <svg viewBox="0 0 24 24" className="size-4" fill="currentColor" aria-hidden>
          <path d="M12 2l2.4 7.6L22 12l-7.6 2.4L12 22l-2.4-7.6L2 12l7.6-2.4z" />
        </svg>
      </span>
      <span className="text-[22px] font-extrabold tracking-tight">Gistar</span>
    </div>
  )
}

export function Shell() {
  const { role, view, setRole, navigate, reset, toastMsg } = useGistar()
  const session = useApiSession()
  const allowedRoles = useMemo(() => (API_MODE && session.me ? uiRolesFor(session.me) : null), [session.me])
  const Screen = (API_MODE ? API_SCREENS[view] : undefined) ?? SCREENS[view] ?? Dashboard

  // In API mode the role is never free: it comes from the server-side assignments of the session.
  useEffect(() => {
    if (allowedRoles && !allowedRoles.includes(role)) setRole(allowedRoles[0])
  }, [allowedRoles, role, setRole])

  if (API_MODE && session.loading) return <p className="p-10 text-sm text-muted">Conectando con la API…</p>
  if (API_MODE && !session.me) return <LoginScreen />

  return (
    <div className="min-h-screen md:flex">
      <aside className="bg-navy md:sticky md:top-0 md:flex md:h-screen md:w-64 md:shrink-0 md:flex-col md:py-6">
        <div className="flex items-center justify-between px-2 py-3 md:block md:px-3 md:py-0">
          <Logo />
        </div>
        <p className="mt-8 hidden px-6 text-[11px] font-semibold uppercase tracking-[0.14em] text-[#8fb0c6] md:block">Menú · {ROLES[role]}</p>
        <nav aria-label="Navegación principal" className="flex gap-1 overflow-x-auto px-3 pb-3 md:mt-3 md:grid md:overflow-visible md:pb-0">
          {MENUS[role].map((v) => {
            const { label, icon: Icon } = VIEWS[v]
            const active = v === view
            return (
              <button
                key={v}
                type="button"
                onClick={() => navigate(v)}
                aria-current={active ? 'page' : undefined}
                className={`flex shrink-0 cursor-pointer items-center gap-3 whitespace-nowrap rounded-xl px-3.5 py-2.5 text-left text-sm font-medium transition-colors ${
                  active ? 'bg-white/12 text-white' : 'text-[#c4d8e5] hover:bg-white/6 hover:text-white'
                }`}
              >
                <Icon className={`size-4 ${active ? 'text-gold' : 'text-[#8fb0c6]'}`} aria-hidden />
                {label}
              </button>
            )
          })}
        </nav>
        <footer className="mt-auto hidden px-6 text-xs leading-relaxed text-[#8fb0c6] md:block">
          Gistar v1 · Datos ficticios
          <br />
          Proyecto 2 · Somos F5
        </footer>
      </aside>

      <div className="min-w-0 flex-1">
        <header className="sticky top-0 z-20 flex flex-wrap items-center justify-between gap-3 border-b border-line bg-white/90 px-5 py-3.5 backdrop-blur md:px-8">
          <div className="flex flex-wrap items-center gap-3">
            <span className="text-[15px] font-semibold text-ink">Acompañamos cada trayectoria de aprendizaje</span>
            <span className="rounded-md bg-[#fff0cc] px-2 py-0.5 text-[11px] font-bold tracking-wide text-[#6d5014]">DEMO · Datos sintéticos</span>
          </div>
          <div className="flex items-center gap-2">
            {allowedRoles && session.me && (
              <span className="mr-1 hidden whitespace-nowrap border-r border-line pr-3 text-right text-xs leading-tight text-muted lg:block">
                <b className="block text-sm font-semibold text-ink">{session.me.display_name}</b>
                {session.me.roles.map((r) => `${r.role}${r.scope_id ? ` · ${r.scope_id}` : ''}`).join(' | ') || 'Persona (sin rol interno)'}
              </span>
            )}
            <label htmlFor="role" className="whitespace-nowrap text-sm text-muted">
              {allowedRoles ? 'Actuar como' : 'Ver como'}
            </label>
            <select id="role" className={`${inputCls} w-auto max-w-56 py-2`} value={role} disabled={!!allowedRoles && allowedRoles.length < 2} onChange={(e) => setRole(e.target.value as Role)}>
              {(allowedRoles ?? (Object.keys(ROLES) as Role[])).map((k) => (
                <option key={k} value={k}>
                  {ROLES[k]}
                </option>
              ))}
            </select>
            {allowedRoles && (
              <Button variant="ghost" onClick={session.logout} aria-label="Cerrar sesión">
                <LogOut className="size-4" aria-hidden />
                <span className="hidden sm:inline">Salir</span>
              </Button>
            )}
            <Button variant="ghost" onClick={reset} aria-label="Restablecer demo">
              <RotateCcw className="size-4" aria-hidden />
              <span className="hidden sm:inline">Restablecer</span>
            </Button>
          </div>
        </header>
        <main key={`${role}-${view}`} className="mx-auto max-w-[1400px] px-5 py-8 md:px-8">
          {API_MODE && !API_VIEWS.has(view) && (
            <p className="mb-5 flex items-center gap-2 rounded-xl border border-dashed border-line bg-white px-4 py-2.5 text-xs text-muted">
              <CloudOff className="size-3.5 shrink-0" aria-hidden />
              Esta vista todavía usa los datos locales de demostración del navegador; se conectará a la API en un incremento posterior.
            </p>
          )}
          <Screen />
          <p className="mt-10 border-t border-line pt-5 text-xs text-muted">
            {API_MODE
              ? 'Modo servidor: autenticación, permisos por rol y ámbito, inscripción, expedientes y auditoría los gestiona la API. Datos sintéticos; sin IA, correo ni servicios externos.'
              : 'Prototipo funcional con datos sintéticos. Los permisos son solo de interfaz; no hay autenticación, IA, correo ni servicios externos.'}
          </p>
        </main>
      </div>

      <div
        role="status"
        aria-live="polite"
        className={`fixed bottom-6 right-6 z-50 rounded-xl bg-navy px-5 py-3.5 text-sm text-white shadow-[0_12px_32px_rgba(24,45,66,0.3)] transition-all duration-200 ${
          toastMsg ? 'translate-y-0 opacity-100' : 'pointer-events-none translate-y-2 opacity-0'
        }`}
      >
        {toastMsg}
      </div>
    </div>
  )
}
