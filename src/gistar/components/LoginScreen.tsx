import { useState, type FormEvent } from 'react'
import { LogIn } from 'lucide-react'
import { API_URL } from '../../shared/api/config'
import { useApiSession } from '../../shared/api/session'
import { InscriptionForm } from '../views/api/ApiAdmissions'
import { Button, Card, Field, Notice, Segmented, inputCls } from '../ui'

/** Synthetic demo accounts created by `python -m app.seed`. Password: GISTAR_DEMO_PASSWORD (default documented in api/README). */
const DEMO_ACCOUNTS = [
  ['admin@gistar.example', 'Administración'],
  ['captacion.ia@gistar.example', 'Captación · programa IA'],
  ['captacion.data@gistar.example', 'Captación · programa Data'],
  ['seleccion.ia@gistar.example', 'Selección · convocatoria IA 2027A'],
  ['docente@gistar.example', 'Docente · COH-IA y COH-DATA'],
  ['coordinacion@gistar.example', 'Coordinación (agregados)'],
  ['aspirante-01@example.test', 'Aspirante (persona A-001)'],
  ['coder-01@example.test', 'Coder (persona E-001)'],
] as const

export function LoginScreen() {
  const { login, apiDown } = useApiSession()
  const [tab, setTab] = useState<'login' | 'inscripcion'>('login')
  const [email, setEmail] = useState<string>(DEMO_ACCOUNTS[1][0])
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setBusy(true)
    setError(await login(email, password))
    setBusy(false)
  }

  return (
    <div className="min-h-screen bg-canvas px-4 py-10">
      <div className="mx-auto max-w-xl">
        <div className="mb-6 flex items-center gap-2.5">
          <span className="flex size-9 items-center justify-center rounded-lg bg-navy text-gold">
            <svg viewBox="0 0 24 24" className="size-4" fill="currentColor" aria-hidden>
              <path d="M12 2l2.4 7.6L22 12l-7.6 2.4L12 22l-2.4-7.6L2 12l7.6-2.4z" />
            </svg>
          </span>
          <span className="text-2xl font-extrabold tracking-tight text-navy">Gistar</span>
          <span className="ml-auto rounded-md bg-[#fff0cc] px-2 py-0.5 text-[11px] font-bold text-[#6d5014]">DEMO · Datos sintéticos</span>
        </div>
        {apiDown && <Notice tone="warning">No se puede conectar con la API en {API_URL}. Arranca el backend (ver api/README.md).</Notice>}
        <div className="mb-4">
          <Segmented label="Acceso" value={tab} onChange={setTab} options={[{ id: 'login', label: 'Iniciar sesión' }, { id: 'inscripcion', label: 'Quiero inscribirme' }]} />
        </div>
        {tab === 'login' ? (
          <Card title="Iniciar sesión">
            <form onSubmit={submit} className="grid gap-4">
              <Field label="Cuenta de demostración" htmlFor="lg-email">
                <select id="lg-email" className={inputCls} value={email} onChange={(e) => setEmail(e.target.value)}>
                  {DEMO_ACCOUNTS.map(([e, label]) => (
                    <option key={e} value={e}>
                      {label} — {e}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Contraseña" htmlFor="lg-pass" hint="Contraseña de las cuentas sintéticas (api/README.md).">
                <input id="lg-pass" type="password" autoComplete="current-password" className={inputCls} value={password} onChange={(e) => setPassword(e.target.value)} required />
              </Field>
              {error && <Notice tone="warning">{error}</Notice>}
              <div>
                <Button type="submit" disabled={busy}>
                  <LogIn className="size-4" aria-hidden /> {busy ? 'Entrando…' : 'Entrar'}
                </Button>
              </div>
            </form>
            <p className="mt-4 text-xs text-muted">Cada pestaña mantiene su propia sesión: abre otra pestaña para actuar con otro perfil a la vez. Los permisos los comprueba la API.</p>
          </Card>
        ) : (
          <Card title="Solicitud de acceso">
            <InscriptionForm />
          </Card>
        )}
      </div>
    </div>
  )
}
