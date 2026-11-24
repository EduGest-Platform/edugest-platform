import { useEffect, useRef, useState, type FormEvent } from "react"
import { api, errorMessage, type Schemas } from "../../../shared/api/client"
import {
  Button,
  Card,
  Field,
  Notice,
  PageTitle,
  Table,
  inputCls,
} from "../../ui"
import { useAcademicCohorts, type AcademicCohort } from "./ApiCohorts"

export function AttendanceTotals({
  summary,
}: {
  summary: Schemas["AttendanceSummary"]
}) {
  const totals = summary.cohort_totals
  return (
    <div className="grid gap-3 text-sm">
      <p>{summary.rule}</p>
      {totals.suppressed ? (
        <Notice>
          Agregado oculto por tamaño mínimo del grupo. No equivale a cero.
        </Notice>
      ) : (
        <p>
          Asistidos: {totals.attended_days ?? "Sin dato"} · Ausencia
          justificada: {totals.justified_absence_days ?? "Sin dato"} · No
          justificada: {totals.unjustified_absence_days ?? "Sin dato"} · Sin
          registrar: {totals.unrecorded_days ?? "Sin dato"}
        </p>
      )}
      {!!summary.items.length && (
        <Table
          head={[
            "Matrícula",
            "Asistidos",
            "Retraso",
            "Justificada",
            "No justificada",
            "Sin dato",
            "Tasa registrada",
          ]}
        >
          {summary.items.map((item) => (
            <tr key={item.enrollment_id}>
              <td className="font-mono text-xs">{item.enrollment_id}</td>
              <td>{item.attended_days}</td>
              <td>{item.late_days}</td>
              <td>{item.justified_absence_days}</td>
              <td>{item.unjustified_absence_days}</td>
              <td>{item.unrecorded_days}</td>
              <td>
                {item.attendance_rate === null
                  ? "Sin registros"
                  : `${(100 * item.attendance_rate).toFixed(1)} %`}
              </td>
            </tr>
          ))}
        </Table>
      )}
    </div>
  )
}

function CohortAttendance({ cohort }: { cohort: AcademicCohort }) {
  const [summary, setSummary] = useState<Schemas["AttendanceSummary"] | null>(
    null,
  )
  const [sessions, setSessions] = useState<Schemas["SessionOut"][]>([])
  const [attempt, setAttempt] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const [notice, setNotice] = useState("")
  const [busy, setBusy] = useState(false)
  const lock = useRef(false)
  const alive = useRef(true)
  const [sessionId, setSessionId] = useState("")
  const [enrollmentId, setEnrollmentId] = useState("")
  const [status, setStatus] =
    useState<Schemas["RecordWrite"]["status"]>("presente")
  const [modality, setModality] = useState<"presencial" | "online">(
    "presencial",
  )
  const [justification, setJustification] =
    useState<"justificada" | "no_justificada">("no_justificada")
  const [reason, setReason] = useState("")
  const [date, setDate] = useState("")
  const [shift, setShift] =
    useState<Schemas["SessionWrite"]["shift"]>("completa")
  useEffect(() => {
    alive.current = true
    return () => {
      alive.current = false
    }
  }, [])
  useEffect(() => {
    const controller = new AbortController()
    setLoading(true)
    setError("")
    setSummary(null)
    setSessions([])
    void (async () => {
      try {
        const totals = await api.GET(
          "/api/v1/cohorts/{cohort_id}/attendance-summary",
          {
            params: { path: { cohort_id: cohort.id } },
            signal: controller.signal,
          },
        )
        if (controller.signal.aborted) return
        if (!totals.data) {
          setError(errorMessage(totals.error))
          return
        }
        setSummary(totals.data)
        if (cohort.can_record_attendance) {
          const result = await api.GET(
            "/api/v1/cohorts/{cohort_id}/attendance-sessions",
            {
              params: { path: { cohort_id: cohort.id } },
              signal: controller.signal,
            },
          )
          if (controller.signal.aborted) return
          if (result.data) setSessions(result.data.items)
          else {
            setSummary(null)
            setError(errorMessage(result.error))
          }
        }
      } catch {
        if (!controller.signal.aborted)
          setError("No se pudo cargar la asistencia.")
      } finally {
        if (!controller.signal.aborted) setLoading(false)
      }
    })()
    return () => controller.abort()
  }, [cohort.id, cohort.can_record_attendance, attempt])
  const selectedSession = sessions.find((s) => s.id === sessionId)
  const correction = !!selectedSession?.records.some(
    (r) => r.enrollment_id === enrollmentId,
  )
  const save = async (event: FormEvent, create: boolean) => {
    event.preventDefault()
    if (lock.current) return
    if (
      !create &&
      (!selectedSession?.held ||
        !summary?.items.some((i) => i.enrollment_id === enrollmentId))
    )
      return
    lock.current = true
    setBusy(true)
    setError("")
    setNotice("")
    try {
      const result = create
        ? await api.POST("/api/v1/cohorts/{cohort_id}/attendance-sessions", {
            params: { path: { cohort_id: cohort.id } },
            body: { session_date: date, shift },
          })
        : await api.PUT(
            "/api/v1/attendance-sessions/{session_id}/records/{enrollment_id}",
            {
              params: {
                path: { session_id: sessionId, enrollment_id: enrollmentId },
              },
              body: {
                status,
                modality: status === "ausente" ? null : modality,
                justification: status === "ausente" ? justification : null,
                reason: reason.trim() || null,
              },
            },
          )
      if (!alive.current) return
      if (!result.data) {
        setError(errorMessage(result.error))
        return
      }
      setReason("")
      setNotice(
        create
          ? "Sesión creada en el servidor."
          : "Asistencia registrada y auditada por el servidor.",
      )
      setAttempt((x) => x + 1)
    } catch {
      if (alive.current)
        setError(
          "No se pudo confirmar la operación. Actualiza antes de repetirla.",
        )
    } finally {
      lock.current = false
      if (alive.current) setBusy(false)
    }
  }
  return (
    <Card
      title={cohort.nombre}
      action={
        <Button
          variant="ghost"
          disabled={busy}
          onClick={() => setAttempt((x) => x + 1)}
        >
          Actualizar asistencia
        </Button>
      }
    >
      <p className="text-xs">
        Zona horaria de la cohorte: {cohort.timezone}. Matrículas identificadas
        por su UUID del servidor.
      </p>
      {loading && <Notice live="polite">Cargando asistencia…</Notice>}
      {error && (
        <Notice tone="warning" live="assertive">
          {error}
        </Notice>
      )}
      {notice && <Notice live="polite">{notice}</Notice>}
      {!loading && !error && summary && <AttendanceTotals summary={summary} />}
      {cohort.can_record_attendance && !loading && !error && summary && (
        <div className="mt-6 grid gap-6">
          <form onSubmit={(e) => void save(e, true)} className="grid gap-3">
            <h3 className="font-semibold">Crear sesión</h3>
            <Field label="Fecha local de la cohorte" htmlFor="attendance-date">
              <input
                id="attendance-date"
                type="date"
                className={inputCls}
                value={date}
                min={cohort.inicio}
                max={cohort.fin}
                required
                disabled={busy}
                onChange={(e) => setDate(e.target.value)}
              />
            </Field>
            <Field label="Jornada" htmlFor="attendance-shift">
              <select
                id="attendance-shift"
                className={inputCls}
                value={shift}
                disabled={busy}
                onChange={(e) => setShift(e.target.value as typeof shift)}
              >
                <option value="completa">Completa · 1</option>
                <option value="manana">Mañana · 0,5</option>
                <option value="tarde">Tarde · 0,5</option>
              </select>
            </Field>
            <Button type="submit" disabled={busy}>
              Crear sesión
            </Button>
          </form>
          <form onSubmit={(e) => void save(e, false)} className="grid gap-3">
            <h3 className="font-semibold">Registrar o corregir asistencia</h3>
            <Field label="Sesión celebrada" htmlFor="attendance-session">
              <select
                id="attendance-session"
                className={inputCls}
                value={sessionId}
                required
                disabled={busy}
                onChange={(e) => {
                  setSessionId(e.target.value)
                  setReason("")
                }}
              >
                <option value="">Selecciona una sesión</option>
                {sessions
                  .filter((s) => s.held)
                  .map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.session_date} · {s.shift} · {s.duration_fraction}
                    </option>
                  ))}
              </select>
            </Field>
            <Field label="Matrícula" htmlFor="attendance-enrollment">
              <select
                id="attendance-enrollment"
                className={inputCls}
                value={enrollmentId}
                required
                disabled={busy}
                onChange={(e) => {
                  setEnrollmentId(e.target.value)
                  setReason("")
                }}
              >
                <option value="">Selecciona una matrícula</option>
                {summary.items.map((i) => (
                  <option key={i.enrollment_id} value={i.enrollment_id}>
                    {i.enrollment_id}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Estado observado" htmlFor="attendance-status">
              <select
                id="attendance-status"
                className={inputCls}
                value={status}
                disabled={busy}
                onChange={(e) => setStatus(e.target.value as typeof status)}
              >
                <option value="presente">Presente</option>
                <option value="retraso">Retraso</option>
                <option value="ausente">Ausente</option>
              </select>
            </Field>
            {status === "ausente" ? (
              <Field label="Justificación" htmlFor="attendance-justification">
                <select
                  id="attendance-justification"
                  className={inputCls}
                  value={justification}
                  disabled={busy}
                  onChange={(e) =>
                    setJustification(e.target.value as typeof justification)
                  }
                >
                  <option value="justificada">Justificada</option>
                  <option value="no_justificada">No justificada</option>
                </select>
              </Field>
            ) : (
              <Field label="Modalidad" htmlFor="attendance-modality">
                <select
                  id="attendance-modality"
                  className={inputCls}
                  value={modality}
                  disabled={busy}
                  onChange={(e) =>
                    setModality(e.target.value as typeof modality)
                  }
                >
                  <option value="presencial">Presencial</option>
                  <option value="online">Online</option>
                </select>
              </Field>
            )}
            <Field
              label={
                correction
                  ? "Motivo de corrección obligatorio (sin datos de salud)"
                  : "Motivo operativo opcional (sin datos de salud)"
              }
              htmlFor="attendance-reason"
            >
              <input
                id="attendance-reason"
                className={inputCls}
                value={reason}
                required={correction}
                maxLength={300}
                disabled={busy}
                onChange={(e) => setReason(e.target.value)}
              />
            </Field>
            <Button
              type="submit"
              disabled={
                busy ||
                !selectedSession?.held ||
                !enrollmentId ||
                (correction && !reason.trim())
              }
            >
              Guardar asistencia
            </Button>
          </form>
        </div>
      )}
    </Card>
  )
}

export function ApiAttendance() {
  const { cohorts, loading, error, retry } = useAcademicCohorts()
  const [selected, setSelected] = useState("")
  const cohort = cohorts.find((c) => c.id === selected) ?? cohorts[0]
  return (
    <>
      <PageTitle
        title="Asistencia"
        sub="Registros del servidor: jornada completa 1; media jornada 0,5. Sin dato no significa ausencia."
      />
      {loading && <Notice live="polite">Cargando cohortes…</Notice>}
      {error && (
        <Notice tone="warning" live="assertive">
          {error}
          <Button onClick={retry}>Reintentar</Button>
        </Notice>
      )}
      {!loading && !error && !cohort && (
        <Notice>No hay cohortes académicas autorizadas.</Notice>
      )}
      {cohort && (
        <>
          <Field label="Cohorte" htmlFor="attendance-cohort">
            <select
              id="attendance-cohort"
              className={inputCls}
              value={cohort.id}
              onChange={(e) => setSelected(e.target.value)}
            >
              {cohorts.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.nombre}
                </option>
              ))}
            </select>
          </Field>
          <CohortAttendance key={cohort.id} cohort={cohort} />
        </>
      )}
    </>
  )
}
