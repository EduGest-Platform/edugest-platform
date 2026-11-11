import { useState } from 'react'
import { Search, Signature, ChevronRight } from 'lucide-react'
import { APP_STATES, FINAL_STATES, humanize } from '../config'
import { useGistar } from '../store'
import type { Candidatura } from '../types'
import { Button, Card, Field, Notice, PageTitle, Status, Table, inputCls } from '../ui'

const CHECK_FIELDS = ['asistencia_jornada', 'ejercicio_acceso', 'taller_recomendado', 'entrevista'] as const
const CHECK_OPTIONS = ['pendiente', 'asistio', 'entregado', 'realizada', 'completada', 'no_consta']

export function Applications() {
  const { data } = useGistar()
  const [filter, setFilter] = useState('')
  const [selected, setSelected] = useState('A-006')
  const q = filter.toLowerCase()
  const apps = data.candidaturas.filter((a) => a.nombre_ficticio.toLowerCase().includes(q) || a.id.toLowerCase().includes(q))
  const current = data.candidaturas.find((a) => a.id === selected) ?? data.candidaturas[0]

  return (
    <>
      <PageTitle title="Candidaturas" sub="Consulta y seguimiento de procesos de admisión con revisión humana." />
      <div className="grid gap-5 xl:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)]">
        <Card
          title="Bandeja de selección"
          action={<span className="text-xs text-muted">{apps.length} resultados</span>}
        >
          <div className="relative mb-4">
            <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-slate-400" aria-hidden />
            <input
              aria-label="Buscar candidaturas"
              placeholder="Buscar nombre o ID"
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              className={`${inputCls} pl-9`}
            />
          </div>
          <Table head={['ID', 'Aspirante', 'Programa', 'Estado', '']}>
            {apps.map((a) => (
              <tr key={a.id} className={a.id === current.id ? 'bg-mist/60' : ''}>
                <td className="pl-2 font-mono text-xs text-muted">{a.id}</td>
                <td className="font-medium">{a.nombre_ficticio}</td>
                <td className="text-muted">{a.programa_id}</td>
                <td>
                  <Status s={a.estado} />
                </td>
                <td className="text-right">
                  <Button size="sm" variant={a.id === current.id ? 'primary' : 'ghost'} onClick={() => setSelected(a.id)}>
                    Revisar <ChevronRight className="size-3.5" aria-hidden />
                  </Button>
                </td>
              </tr>
            ))}
          </Table>
        </Card>
        <ApplicationDetail key={current.id} app={current} />
      </div>
    </>
  )
}

function ApplicationDetail({ app }: { app: Candidatura }) {
  const { data, role, update, toast } = useGistar()
  const [recommendation, setRecommendation] = useState(app.recomendacion_preliminar ?? '')
  const [outcome, setOutcome] = useState<string>('admitida')
  const canEdit = role === 'seleccion'
  const reviewer = role === 'docente' || role === 'fundacion'
  const idx = APP_STATES.indexOf(app.estado as (typeof APP_STATES)[number])
  const next = idx >= 0 ? APP_STATES[idx + 1] : undefined
  const programa = data.programas.find((p) => p.id === app.programa_id)
  const vd = app.validacion_docente
  const vf = app.validacion_fundacion
  const signaturesMatch = !!vd && !!vf && vd.resultado === vf.resultado
  const isFinal = (FINAL_STATES as readonly string[]).includes(app.estado)
  const mutateApp = (fn: (a: Candidatura) => void) => (d: typeof data) => fn(d.candidaturas.find((x) => x.id === app.id)!)

  const confirmDecision = () => {
    if (!signaturesMatch) return toast('Faltan firmas humanas coincidentes')
    update(
      mutateApp((a) => {
        a.estado = vd!.resultado
        a.decision_final = vd!.resultado
      }),
      'decision_final_humana',
      app.id,
    )
  }

  return (
    <Card
      className="xl:sticky xl:top-24 xl:self-start"
      title={
        <span>
          <span className="font-mono text-sm text-muted">{app.id}</span> · {app.nombre_ficticio}
        </span>
      }
      action={<Status s={app.estado} />}
    >
      <p className="-mt-2 text-sm text-muted">
        {programa?.nombre} · {app.email_demo}
      </p>
      <div className="my-5 border-t border-line" />
      <div className="grid gap-4 sm:grid-cols-2">
        {CHECK_FIELDS.map((k) => (
          <Field key={k} label={humanize(k)} htmlFor={`f-${k}`}>
            <select
              id={`f-${k}`}
              className={inputCls}
              disabled={!canEdit}
              value={app[k]}
              onChange={(e) => update(mutateApp((a) => (a[k] = e.target.value)), 'registrar_' + k, app.id)}
            >
              {CHECK_OPTIONS.map((o) => (
                <option key={o} value={o}>
                  {humanize(o)}
                </option>
              ))}
            </select>
          </Field>
        ))}
      </div>
      {!canEdit && <p className="mt-3 text-xs text-muted">Solo el rol Selección puede registrar los hitos de evaluación.</p>}

      <div className="mt-6 grid gap-3">
        <Field label="Recomendación preliminar (no es decisión)" htmlFor="recommend">
          <textarea
            id="recommend"
            className={`${inputCls} min-h-24`}
            disabled={!canEdit}
            value={recommendation}
            placeholder={canEdit ? 'Observaciones para el equipo docente y la fundación' : 'Sin recomendación registrada'}
            onChange={(e) => setRecommendation(e.target.value)}
          />
        </Field>
        {canEdit && (
          <div className="flex flex-wrap gap-2">
            <Button variant="ghost" onClick={() => update(mutateApp((a) => (a.recomendacion_preliminar = recommendation)), 'recomendacion_preliminar', app.id)}>
              Guardar recomendación
            </Button>
            {next && (
              <Button onClick={() => update(mutateApp((a) => (a.estado = next)), 'avance_candidatura', app.id)}>
                Avanzar a {humanize(next)}
              </Button>
            )}
          </div>
        )}
      </div>

      <div className="mt-6 rounded-xl bg-mist/70 p-4">
        <h3 className="mb-3 text-sm font-semibold">Revisión humana</h3>
        <div className="grid gap-2 text-sm sm:grid-cols-2">
          <SignatureRow who="Docente" v={vd?.resultado} />
          <SignatureRow who="Fundación" v={vf?.resultado} />
        </div>
        {reviewer && app.estado === 'pendiente_decision_humana' && (
          <div className="mt-4 flex flex-wrap items-end gap-2">
            <div className="min-w-44 flex-1">
              <Field label="Propuesta de decisión" htmlFor="outcome">
                <select id="outcome" className={inputCls} value={outcome} onChange={(e) => setOutcome(e.target.value)}>
                  <option value="admitida">Admitida</option>
                  <option value="lista_espera">Lista de espera</option>
                  <option value="no_admitida">No admitida</option>
                </select>
              </Field>
            </div>
            <Button
              variant="success"
              onClick={() =>
                update(
                  mutateApp((a) => (a[`validacion_${role as 'docente' | 'fundacion'}`] = { resultado: outcome, fecha: data.meta.fecha_simulada })),
                  'firma_humana',
                  app.id,
                )
              }
            >
              <Signature className="size-4" aria-hidden /> Firmar revisión
            </Button>
          </div>
        )}
        {reviewer && !isFinal && signaturesMatch && (
          <Button className="mt-3" onClick={confirmDecision}>
            Confirmar decisión: {humanize(vd!.resultado)}
          </Button>
        )}
        {reviewer && !isFinal && vd && vf && !signaturesMatch && (
          <Notice tone="warning">Las firmas no coinciden. Es necesario acordar la propuesta antes de confirmar.</Notice>
        )}
        {isFinal && <p className="mt-3 text-sm text-muted">Decisión final registrada: <b className="text-ink">{humanize(app.estado)}</b></p>}
      </div>
    </Card>
  )
}

function SignatureRow({ who, v }: { who: string; v?: string }) {
  return (
    <div className="flex items-center justify-between gap-2 rounded-lg bg-white px-3 py-2">
      <span className="text-muted">{who}</span>
      {v ? <Status s={v} /> : <span className="text-xs text-slate-400">sin validar</span>}
    </div>
  )
}
