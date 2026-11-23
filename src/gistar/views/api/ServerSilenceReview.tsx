import { useEffect, useState } from "react"
import { api, type Schemas } from "../../../shared/api/client"
import { describeApiError, problemText } from "../../../shared/api/errors"
import { Button, Card, Notice, Status } from "../../ui"

type Item = Schemas["SilenceReviewItem"]
const date = (value: string) =>
  new Intl.DateTimeFormat("es-ES", {
    dateStyle: "medium",
    timeZone: "Europe/Madrid",
  }).format(new Date(value))

/** Displays server evidence only. Thresholds and stage decisions stay in the backend/human workflow. */
export function SilenceAlertList({
  items,
  onOpen,
}: {
  items: readonly Item[]
  onOpen: (id: string) => void
}) {
  if (!items.length)
    return (
      <p className="text-sm text-muted">
        No hay alertas de silencio en esta convocatoria.
      </p>
    )
  return (
    <ul className="grid gap-3 md:grid-cols-2">
      {items.map((item) => (
        <li
          key={item.application_id}
          data-silence-application={item.application_id}
          className="rounded-xl border border-line p-3 text-sm"
        >
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="font-semibold">
              {item.display_name} · {item.codigo}
            </p>
            <Status s={item.stage} />
          </div>
          <p className="mt-2 font-medium">
            {item.evidence.alert_level === "accion"
              ? "Revisión por plazo y contactos"
              : item.evidence.alert_level === "leve"
                ? "Aviso temprano de contacto"
                : "Alerta pendiente de revisión"}
          </p>
          <p>
            {item.evidence.unanswered_attempts} intentos sin respuesta · aviso
            desde {item.evidence.silence_warning_contacts} intentos
          </p>
          <p>
            Umbral de acción: {item.evidence.silence_max_contacts} intentos y{" "}
            {item.evidence.silence_days} días.
          </p>
          <p className="text-muted">
            {item.evidence.last_attempt_at
              ? `Último intento: ${date(item.evidence.last_attempt_at)}`
              : "Último intento sin fecha confirmada"}
            {item.evidence.days_without_response !== null &&
              ` · ${item.evidence.days_without_response} días sin respuesta`}
          </p>
          <p className="mt-1">
            {item.evidence.threshold_met
              ? "El servidor indica que corresponde revisión humana. La candidatura sigue abierta hasta una decisión autorizada."
              : "No se cumple el umbral de acción. Este aviso no cierra la candidatura."}
          </p>
          <Button
            size="sm"
            variant="ghost"
            className="mt-2"
            onClick={() => onOpen(item.application_id)}
          >
            Abrir expediente
          </Button>
        </li>
      ))}
    </ul>
  )
}

export function ServerSilenceReview({
  callId,
  onOpen,
}: {
  callId: string
  onOpen: (id: string) => void
}) {
  const [reload, setReload] = useState(0)
  const [state, setState] = useState<{
    scope: string
    data?: Schemas["SilenceReviewList"]
    error?: string
  } | null>(null)
  useEffect(() => {
    setState(null)
    if (!callId) return
    let active = true
    const controller = new AbortController()
    async function load() {
      try {
        const result = await api.GET("/api/v1/calls/{call_id}/silence-review", {
          params: { path: { call_id: callId } },
          signal: controller.signal,
        })
        if (!active) return
        if (!result.data) {
          setState({
            scope: callId,
            error: problemText(
              describeApiError(result.response.status, result.error),
            ),
          })
        } else if (result.data.call_id !== callId) {
          setState({
            scope: callId,
            error:
              "Las alertas no corresponden a esta convocatoria. Vuelve a actualizar.",
          })
        } else {
          setState({ scope: callId, data: result.data })
        }
      } catch {
        if (active)
          setState({
            scope: callId,
            error:
              "No se han podido consultar las alertas. Inténtalo de nuevo.",
          })
      }
    }
    void load()
    return () => {
      active = false
      controller.abort()
    }
  }, [callId, reload])
  const current = state?.scope === callId ? state : null
  return (
    <Card
      title="Alertas de silencio para revisión humana"
      action={
        <Button
          size="sm"
          variant="ghost"
          disabled={!callId}
          onClick={() => setReload((value) => value + 1)}
        >
          Actualizar alertas
        </Button>
      }
    >
      <section
        data-silence-review
        aria-label="Alertas de silencio"
        className="grid gap-3"
      >
        {!callId ? (
          <p>Selecciona una convocatoria para consultar sus alertas.</p>
        ) : (
          <>
            <p className="text-sm text-muted">
              Estas alertas corresponden a toda la convocatoria seleccionada.
              Consulta de solo lectura; no se cierran candidaturas
              automáticamente.
            </p>
            {!current && <p role="status">Cargando alertas…</p>}
            {current?.error && (
              <Notice tone="warning" live="assertive">
                {current.error}
              </Notice>
            )}
            {current?.data && (
              <SilenceAlertList items={current.data.items} onOpen={onOpen} />
            )}
          </>
        )}
      </section>
    </Card>
  )
}
