import { useState, type FormEvent } from 'react'
import { Check, Send } from 'lucide-react'
import { APP_STATES, ASPIRANT_ID, humanize } from '../config'
import { useGistar } from '../store'
import { Button, Card, Field, Notice, PageTitle, Status, inputCls } from '../ui'

export function Inscription() {
  const { data, update, navigate } = useGistar()
  const a = data.candidaturas.find((x) => x.id === ASPIRANT_ID)!
  const locked = a.estado !== 'borrador'
  const [form, setForm] = useState({
    name: a.nombre_ficticio,
    email: a.email_demo,
    motivation: a.motivacion,
    availability: a.disponibilidad ?? 'Mañana',
    accepted: locked,
  })

  const submit = (e: FormEvent) => {
    e.preventDefault()
    update(
      (d) => {
        const c = d.candidaturas.find((x) => x.id === ASPIRANT_ID)!
        c.nombre_ficticio = form.name
        c.email_demo = form.email
        c.motivacion = form.motivation
        c.disponibilidad = form.availability
        c.estado = 'enviada'
      },
      'envio_candidatura',
      ASPIRANT_ID,
    )
    navigate('candidatura')
  }

  return (
    <>
      <PageTitle title="Inscripción" sub="Completa los datos ficticios del formulario de acceso." />
      <Card title="Solicitud de acceso" action={locked ? <Status s={a.estado} /> : undefined} className="max-w-2xl">
        {locked && <Notice>Tu candidatura ya se ha enviado. Los datos no pueden modificarse.</Notice>}
        <form onSubmit={submit} className="grid gap-4">
          <Field label="Nombre de demostración" htmlFor="name">
            <input id="name" className={inputCls} required disabled={locked} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          </Field>
          <Field label="Correo electrónico de demostración" htmlFor="email">
            <input id="email" type="email" className={inputCls} required disabled={locked} value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
          </Field>
          <Field label="Motivación" htmlFor="motivation">
            <textarea id="motivation" className={`${inputCls} min-h-28`} required disabled={locked} value={form.motivation} onChange={(e) => setForm({ ...form, motivation: e.target.value })} />
          </Field>
          <Field label="Disponibilidad" htmlFor="availability">
            <select id="availability" className={inputCls} disabled={locked} value={form.availability} onChange={(e) => setForm({ ...form, availability: e.target.value })}>
              {['Mañana', 'Tarde', 'Flexible'].map((o) => (
                <option key={o}>{o}</option>
              ))}
            </select>
          </Field>
          <label className="flex items-start gap-2.5 text-sm">
            <input type="checkbox" className="mt-0.5 size-4 accent-teal" required disabled={locked} checked={form.accepted} onChange={(e) => setForm({ ...form, accepted: e.target.checked })} />
            Entiendo que esta plataforma utiliza datos sintéticos
          </label>
          {!locked && (
            <div className="border-t border-line pt-4">
              <Button type="submit">
                <Send className="size-4" aria-hidden /> Enviar candidatura
              </Button>
            </div>
          )}
        </form>
      </Card>
    </>
  )
}

export function MyApplication() {
  const { data } = useGistar()
  const a = data.candidaturas.find((x) => x.id === ASPIRANT_ID)!
  const programa = data.programas.find((p) => p.id === a.programa_id)
  const steps = [...APP_STATES, a.decision_final ?? 'decision_final']
  const current = steps.indexOf(a.estado)
  const reached = current === -1 ? steps.length - 1 : current

  return (
    <>
      <PageTitle title="Mi candidatura" sub="Sigue el estado de tu proceso de acceso." />
      <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.2fr)]">
        <Card title={`Solicitud · ${a.id}`}>
          <dl className="grid gap-3 text-sm">
            <Row k="Aspirante" v={a.nombre_ficticio} />
            <Row k="Correo" v={a.email_demo} />
            <Row k="Programa" v={programa?.nombre} />
            <div className="flex items-center justify-between gap-3">
              <dt className="text-muted">Estado actual</dt>
              <dd>
                <Status s={a.estado} />
              </dd>
            </div>
          </dl>
          <Notice>La evaluación y la admisión requieren revisión humana. La plataforma no toma decisiones automáticas.</Notice>
        </Card>
        <Card title="Hitos del proceso">
          <ol className="relative grid gap-0">
            {steps.map((s, i) => {
              const done = i < reached || (i === reached && i === steps.length - 1)
              const active = i === reached
              return (
                <li key={s} className="relative flex gap-3 pb-5 last:pb-0">
                  {i < steps.length - 1 && <span className={`absolute left-[11px] top-6 h-[calc(100%-20px)] w-px ${i < reached ? 'bg-teal' : 'bg-line'}`} />}
                  <span
                    className={`relative z-10 flex size-6 shrink-0 items-center justify-center rounded-full text-[11px] font-bold ${
                      done ? 'bg-teal text-white' : active ? 'bg-navy text-white ring-4 ring-navy/10' : 'border border-line bg-white text-slate-400'
                    }`}
                  >
                    {done ? <Check className="size-3.5" aria-hidden /> : i + 1}
                  </span>
                  <span className={`pt-0.5 text-sm capitalize ${active ? 'font-semibold text-ink' : i < reached ? 'text-ink/80' : 'text-muted'}`}>
                    {humanize(s)}
                    {active && <span className="ml-2 text-xs font-normal normal-case text-teal-700">· estado actual</span>}
                  </span>
                </li>
              )
            })}
          </ol>
        </Card>
      </div>
    </>
  )
}

function Row({ k, v }: { k: string; v?: string }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <dt className="text-muted">{k}</dt>
      <dd className="text-right font-medium">{v}</dd>
    </div>
  )
}
