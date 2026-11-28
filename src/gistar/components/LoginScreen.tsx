import { useEffect, useState, type FormEvent } from 'react'
import { LogIn } from 'lucide-react'
import { API_URL } from '../../shared/api/config'
import { useApiSession } from '../../shared/api/session'
import { InscriptionForm } from '../views/api/ApiAdmissions'
import { PublicCatalog } from '../views/api/PublicCatalog'
import { Button, Card, Field, Notice, inputCls } from '../ui'
import { AppearanceControls, type AppearancePreferences } from './AppearanceControls'
import { PublicAccessNavigation } from './PublicAccessNavigation'
import { publicAccessUrl, readPublicAccess, type PublicAccessLocation } from './publicAccessLocation'

/** Synthetic demo accounts created by `python -m app.seed`. Password: GISTAR_DEMO_PASSWORD (default documented in api/README). */
const DEMO_ACCOUNTS = [
  ['admin@gistar.example', 'Administración', 'Administration'],
  ['captacion.ia@gistar.example', 'Captación · programa IA', 'Recruitment · AI programme'],
  ['captacion.data@gistar.example', 'Captación · programa Data', 'Recruitment · Data programme'],
  ['seleccion.ia@gistar.example', 'Selección · convocatoria IA 2027A', 'Selection · AI intake 2027A'],
  ['docente@gistar.example', 'Docente · COH-IA y COH-DATA', 'Teacher · COH-IA and COH-DATA'],
  ['coordinacion@gistar.example', 'Coordinación (agregados)', 'Coordination (aggregates)'],
  ['aspirante-01@example.test', 'Aspirante (persona A-001)', 'Applicant (person A-001)'],
  ['coder-01@example.test', 'Coder (persona E-001)', 'Learner (person E-001)'],
] as const

export function LoginScreen({ appearance }: { appearance: AppearancePreferences }) {
  const { language } = appearance
  const en = language === 'en'
  const { login, apiDown, notice } = useApiSession()
  const [location, setLocation] = useState(() => readPublicAccess(window.location.search))
  const { view: tab, callId } = location
  const [email, setEmail] = useState<string>(DEMO_ACCOUNTS[1][0])
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    function restoreAccess() {
      setLocation(readPublicAccess(window.location.search))
    }
    window.addEventListener('popstate', restoreAccess)
    return () => window.removeEventListener('popstate', restoreAccess)
  }, [])

  useEffect(() => {
    if (callId) document.getElementById('ins-name')?.focus()
  }, [callId])

  function navigateAccess(next: PublicAccessLocation) {
    const url = publicAccessUrl(window.location.href, next)
    if (url.href !== window.location.href) window.history.pushState(null, '', url)
    setLocation(next)
  }

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setBusy(true)
    setError(null)
    setError(await login(email, password))
    setBusy(false)
  }

  return (
    <main className="min-h-screen bg-canvas px-4 py-6 sm:py-10">
      <div className={`mx-auto ${tab === 'catalogo' ? 'max-w-4xl' : 'max-w-xl'}`}>
        <div className="mb-6 flex flex-wrap items-center gap-2.5">
          <span className="flex size-9 items-center justify-center rounded-lg bg-navy text-gold">
            <svg viewBox="0 0 24 24" className="size-4" fill="currentColor" aria-hidden>
              <path d="M12 2l2.4 7.6L22 12l-7.6 2.4L12 22l-2.4-7.6L2 12l7.6-2.4z" />
            </svg>
          </span>
          <span className="text-2xl font-extrabold tracking-tight text-navy">EduGest</span>
          <span className="ml-auto rounded-md bg-[#fff0cc] px-2 py-0.5 text-[11px] font-bold text-[#6d5014]" lang={language}>{en ? 'DEMO · Synthetic data' : 'DEMO · Datos sintéticos'}</span>
        </div>
        <div className="mb-4 flex"><AppearanceControls {...appearance} /></div>
        {tab === 'login' && (
          <section lang={language} aria-labelledby="public-welcome" className="mb-6 rounded-2xl bg-navy px-6 py-7 text-white sm:px-8">
            <h1 id="public-welcome" className="text-2xl font-bold tracking-tight sm:text-3xl">{en ? 'Find your next course' : 'Encuentra tu próxima formación'}</h1>
            <p className="mt-2 max-w-md text-sm leading-relaxed text-white/90">
              {en ? 'Browse open course listings, compare dates and apply for a place.'
                : 'Consulta las convocatorias publicadas, compara fechas y solicita plaza en la formación que te interesa.'}
            </p>
            <Button
              variant="ghost"
              className="mt-5"
              onClick={() => navigateAccess({ view: 'catalogo' })}
            >
              {en ? 'Explore the catalogue' : 'Explorar el catálogo'}
            </Button>
          </section>
        )}
        {notice && !apiDown && (
          <Notice tone="warning" live="polite">
            {notice}
          </Notice>
        )}
        {apiDown && <Notice tone="warning" live="assertive">No se puede conectar con la API en {API_URL}. Arranca el backend (ver api/README.md).</Notice>}
        <div className="mb-4">
          <PublicAccessNavigation language={language} view={tab} onNavigate={(view) => navigateAccess({ view })} />
        </div>
        {tab === 'login' ? (
          <section lang={language}>
            <Card title={en ? 'Sign in' : 'Iniciar sesión'}>
              <form onSubmit={submit} aria-describedby={error ? 'login-error' : undefined} className="grid gap-4">
                <Field label={en ? 'Demo account' : 'Cuenta de demostración'} htmlFor="lg-email">
                  <select id="lg-email" className={inputCls} value={email} onChange={(e) => {
                      setEmail(e.target.value)
                      setError(null)
                    }}>
                    {DEMO_ACCOUNTS.map(([e, esLabel, enLabel]) => (
                      <option key={e} value={e}>
                        {en ? enLabel : esLabel} — {e}
                      </option>
                    ))}
                  </select>
                </Field>
                <Field label={en ? 'Password' : 'Contraseña'} htmlFor="lg-pass">
                  <input
                    id="lg-pass"
                    type="password"
                    autoComplete="current-password"
                    aria-describedby="login-password-help"
                    className={inputCls}
                    value={password}
                    onChange={(e) => {
                      setPassword(e.target.value)
                      setError(null)
                    }}
                    required
                  />
                  <p id="login-password-help" className="text-xs text-muted">{en ? 'Synthetic account password (api/README.md).' : 'Contraseña de las cuentas sintéticas (api/README.md).'}</p>
                </Field>
                {error && (
                  <div id="login-error" lang="es">
                    <Notice tone="warning" live="assertive">
                      {error}
                    </Notice>
                  </div>
                )}
                <div>
                  <Button type="submit" disabled={busy}>
                    <LogIn className="size-4" aria-hidden /> {en ? (busy ? 'Signing in…' : 'Sign in') : (busy ? 'Entrando…' : 'Entrar')}
                  </Button>
                </div>
              </form>
              <p className="mt-4 text-xs text-muted">{en
                ? 'Each tab keeps its own session. Open another tab to use a different role. The API checks permissions.'
                : 'Cada pestaña mantiene su propia sesión: abre otra pestaña para actuar con otro perfil a la vez. Los permisos los comprueba la API.'}</p>
            </Card>
          </section>
        ) : tab === 'catalogo' ? (
          <PublicCatalog onApply={(course) => navigateAccess({ view: 'inscripcion', callId: course.id })} />
        ) : (
          <Card title="Solicitud de acceso">
            {callId && <div className="mb-4 grid gap-2">
              <p className="text-sm">Solicitud para la formación elegida. Enviar no garantiza admisión.</p>
              <Button variant="ghost" onClick={() => navigateAccess({ view: 'catalogo' })}>Volver al catálogo</Button>
            </div>}
            <InscriptionForm key={callId ?? 'general'} initialCallId={callId} />
          </Card>
        )}
      </div>
    </main>
  )
}
