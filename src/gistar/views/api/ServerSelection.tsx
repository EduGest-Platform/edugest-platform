import { useEffect, useRef, useState, type FormEvent } from "react"
import { api, errorMessage, type Schemas } from "../../../shared/api/client"
import { useApiSession } from "../../../shared/api/session"
import { Button, Field, Notice, inputCls } from "../../ui"

type History = Schemas["SelectionDecisionList"]
type Vote = Schemas["SelectionApprovalOut"]

export function SelectionEvidence({ history }: { history: History }) {
  const votes = (items: Vote[]) => (
    <ul>
      {items.map((v, i) => (
        <li key={i}>
          {v.actor ?? "Autor no disponible"} · {v.decision} · {v.reason} ·{" "}
          {v.occurred_at}
        </li>
      ))}
    </ul>
  )
  return (
    <div className="grid gap-3 text-sm">
      <p>
        Quórum actual: {history.quorum} personas. No reconstruye la política
        histórica.
      </p>
      <h4 className="font-semibold">Votos pendientes</h4>
      {history.pending_votes.length ? (
        votes(history.pending_votes)
      ) : (
        <p>No hay votos pendientes.</p>
      )}
      <h4 className="font-semibold">Decisiones aplicadas</h4>
      {history.items.length ? (
        history.items.map((d) => (
          <section key={d.id} className="rounded-lg border border-line p-3">
            <p>
              {d.decision} · {d.reason} · {d.occurred_at}
            </p>
            {d.votes?.length ? (
              votes(d.votes)
            ) : (
              <p>Sin evidencia de votos vinculada.</p>
            )}
          </section>
        ))
      ) : (
        <p>No hay decisiones aplicadas.</p>
      )}
    </div>
  )
}

export function ServerSelection({
  applicationId,
  callId,
  onChanged,
  onDirty,
}: {
  applicationId: string
  callId: string
  onChanged: () => void
  onDirty: (dirty: boolean) => void
}) {
  const { me } = useApiSession()
  const allowed = !!me?.roles.some((r) =>
    ["admin", "seleccion", "coordinacion"].includes(r.role),
  )
  const [history, setHistory] = useState<History | null>(null)
  const [overview, setOverview] = useState<Schemas["SelectionOverview"] | null>(
    null,
  )
  const [error, setError] = useState("")
  const [notice, setNotice] = useState("")
  const [attempt, setAttempt] = useState(0)
  const [decision, setDecision] =
    useState<Schemas["SelectionDecisionWrite"]["decision"]>("lista_espera")
  const [reason, setReason] = useState("")
  const [cohort, setCohort] = useState("")
  const [confirmed, setConfirmed] = useState(false)
  const [busy, setBusy] = useState(false)
  const lock = useRef(false)
  const lifetime = useRef(0)
  useEffect(() => {
    onDirty(!!reason.trim())
  }, [reason, onDirty])
  useEffect(() => {
    const controller = new AbortController()
    const generation = ++lifetime.current
    setHistory(null)
    setOverview(null)
    setError("")
    if (allowed)
      void (async () => {
        try {
          const [h, o] = await Promise.all([
            api.GET(
              "/api/v1/applications/{application_id}/selection-decisions",
              {
                params: { path: { application_id: applicationId } },
                signal: controller.signal,
              },
            ),
            api.GET("/api/v1/calls/{call_id}/selection-overview", {
              params: { path: { call_id: callId } },
              signal: controller.signal,
            }),
          ])
          if (controller.signal.aborted) return
          if (!h.data || !o.data) {
            setError(errorMessage(h.error ?? o.error))
            return
          }
          setHistory(h.data)
          setOverview(o.data)
        } catch {
          if (!controller.signal.aborted)
            setError("No se pudo cargar la selección. Reintenta.")
        }
      })()
    return () => {
      controller.abort()
      if (lifetime.current === generation) lifetime.current++
    }
  }, [applicationId, callId, allowed, attempt])
  if (!allowed) return null
  const submit = async (event: FormEvent) => {
    event.preventDefault()
    if (lock.current || !confirmed || !reason.trim()) return
    lock.current = true
    setBusy(true)
    setError("")
    setNotice("")
    const generation = lifetime.current
    try {
      const result = await api.POST(
        "/api/v1/applications/{application_id}/selection-decisions",
        {
          params: { path: { application_id: applicationId } },
          body: {
            decision,
            reason: reason.trim(),
            cohort_id: decision === "admitida" ? cohort.trim() : null,
          },
        },
      )
      if (generation !== lifetime.current) return
      if (!result.data) {
        setError(errorMessage(result.error))
        return
      }
      setNotice(
        result.response.status === 202
          ? "Voto registrado; la decisión sigue pendiente de acuerdo humano."
          : "Decisión aplicada por el servidor.",
      )
      setReason("")
      setConfirmed(false)
      setAttempt((x) => x + 1)
      onChanged()
    } catch {
      if (generation === lifetime.current) {
        setError(
          "No se pudo confirmar el voto. Recarga antes de volver a enviarlo.",
        )
        setAttempt((x) => x + 1)
      }
    } finally {
      lock.current = false
      setBusy(false)
    }
  }
  return (
    <section className="grid gap-3">
      <h3 className="font-semibold">Deliberación humana</h3>
      {error && (
        <Notice live="assertive" tone="warning">
          {error}
        </Notice>
      )}
      {notice && <Notice live="polite">{notice}</Notice>}
      <Button
        variant="ghost"
        disabled={busy}
        onClick={() => setAttempt((x) => x + 1)}
      >
        Actualizar selección
      </Button>
      {overview && (
        <p className="text-sm">
          Plazas: {overview.plazas} · Admitidas: {overview.admitted} · Libres:{" "}
          {overview.free_places} · En selección: {overview.in_selection} ·
          Reserva: {overview.waiting}. Orden de reserva provisional: entrada en
          lista.
        </p>
      )}
      {overview && (
        <ul className="text-sm">
          {overview.candidates.map((c) => (
            <li key={c.application_id}>
              {c.codigo} · {c.stage_label}
            </li>
          ))}
        </ul>
      )}
      {history && <SelectionEvidence history={history} />}
      {history && (
        <form onSubmit={submit} className="grid gap-3">
          <Field label="Propuesta humana" htmlFor="selection-decision">
            <select
              id="selection-decision"
              className={inputCls}
              value={decision}
              disabled={busy}
              onChange={(e) => {
                setDecision(e.target.value as typeof decision)
                setConfirmed(false)
              }}
            >
              <option value="admitida">Admitida</option>
              <option value="lista_espera">Lista de espera</option>
              <option value="no_admitida">No admitida</option>
            </select>
          </Field>
          {decision === "admitida" && (
            <Field label="ID de cohorte de destino" htmlFor="selection-cohort">
              <input
                id="selection-cohort"
                className={inputCls}
                value={cohort}
                maxLength={20}
                required
                disabled={busy}
                onChange={(e) => {
                  setCohort(e.target.value)
                  setConfirmed(false)
                }}
              />
            </Field>
          )}
          <Field
            label="Motivo operativo, sin datos personales sensibles"
            htmlFor="selection-reason"
          >
            <textarea
              id="selection-reason"
              className={inputCls}
              value={reason}
              maxLength={500}
              required
              disabled={busy}
              onChange={(e) => {
                setReason(e.target.value)
                setConfirmed(false)
              }}
            />
          </Field>
          <label className="text-sm">
            <input
              type="checkbox"
              checked={confirmed}
              disabled={busy}
              onChange={(e) => setConfirmed(e.target.checked)}
            />{" "}
            Confirmo que he revisado esta propuesta y quiero registrar mi voto.
          </label>
          <Button type="submit" disabled={busy || !confirmed || !reason.trim()}>
            Registrar mi voto
          </Button>
          <p className="text-xs">
            La API valida permisos, ámbito, etapa, cupo y firmas distintas. Un
            voto pendiente no equivale a admisión.
          </p>
        </form>
      )}
    </section>
  )
}
