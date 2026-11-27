import { useEffect, useState } from "react"
import { api, errorMessage, type Schemas } from "../../../shared/api/client"
import { Button, Card, Field, Notice, PageTitle, inputCls } from "../../ui"
import { useGistar } from "../../store"
import { useApiSession } from "../../../shared/api/session"
import { AcademicEmail, pendingEmailKey, readPendingEmail } from "./AcademicEmail"

export type AcademicCohort = Schemas["AcademicCohortOut"]

export function useAcademicCohorts() {
  const [cohorts, setCohorts] = useState<AcademicCohort[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const [attempt, setAttempt] = useState(0)
  useEffect(() => {
    const controller = new AbortController()
    setLoading(true)
    setError("")
    setCohorts([])
    void (async () => {
      try {
        const result = await api.GET("/api/v1/cohorts", {
          signal: controller.signal,
        })
        if (controller.signal.aborted) return
        if (result.data) setCohorts(result.data)
        else setError(errorMessage(result.error))
      } catch {
        if (!controller.signal.aborted)
          setError("No se pudo cargar el directorio de cohortes.")
      } finally {
        if (!controller.signal.aborted) setLoading(false)
      }
    })()
    return () => controller.abort()
  }, [attempt])
  return { cohorts, loading, error, retry: () => setAttempt((x) => x + 1) }
}

export function CohortDetails({ cohort }: { cohort: AcademicCohort }) {
  return (
    <dl className="grid gap-2 text-sm">
      <dt>Programa</dt>
      <dd>{cohort.program_id}</dd>
      <dt>Fechas</dt>
      <dd>
        {cohort.inicio} — {cohort.fin}
      </dd>
      <dt>Zona horaria</dt>
      <dd>{cohort.timezone}</dd>
      <dt>Asistencia</dt>
      <dd>
        {cohort.can_record_attendance
          ? "Puede registrar en esta cohorte"
          : "Solo consulta de agregados"}
      </dd>
    </dl>
  )
}

export function ApiCohorts() {
  const { role } = useGistar()
  const { me } = useApiSession()
  const [emailBusy, setEmailBusy] = useState(false)
  const { cohorts, loading, error, retry } = useAcademicCohorts()
  const [selected, setSelected] = useState("")
  const cohort = cohorts.find((c) => c.id === selected) ?? cohorts[0]
  return (
    <>
      <PageTitle
        title="Cohortes"
        sub="Directorio del servidor limitado a tu ámbito académico autorizado."
      />
      <Card
        title="Cursos y cohortes"
        action={
          <Button variant="ghost" onClick={retry} disabled={emailBusy}>
            Actualizar
          </Button>
        }
      >
        {loading && <Notice live="polite">Cargando cohortes…</Notice>}
        {error && (
          <Notice tone="warning" live="assertive">
            {error}
          </Notice>
        )}
        {!loading && !error && !cohort && (
          <Notice>No hay cohortes con permiso académico en tu cuenta.</Notice>
        )}
        {cohort && (
          <>
            <Field label="Cohorte" htmlFor="academic-cohort">
              <select
                id="academic-cohort"
                className={inputCls}
                value={cohort.id}
                disabled={emailBusy}
                onChange={(e) => setSelected(e.target.value)}
              >
                {cohorts.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.nombre}{me && readPendingEmail(pendingEmailKey(me.id, c.id)) ? " · Aviso sin confirmar" : ""}
                  </option>
                ))}
              </select>
            </Field>
            <CohortDetails cohort={cohort} />
          </>
        )}
        <p className="mt-4 text-xs">
          No se muestran datos del alumnado ni se activan cursos desde esta
          pantalla. Los permisos de cada operación se vuelven a comprobar en la
          API.
        </p>
      </Card>
      {me && cohort && (role === "admin" || role === "docente") && (
        <AcademicEmail key={pendingEmailKey(me.id, cohort.id)} cohortId={cohort.id}
          storageKey={pendingEmailKey(me.id, cohort.id)} onBusyChange={setEmailBusy} />
      )}
    </>
  )
}
