import { describe, expect, it } from "vitest"
import { renderToStaticMarkup } from "react-dom/server"
import type { Schemas } from "../../shared/api/client"
import { AttendanceTotals } from "../views/api/ApiAttendance"

const base: Schemas["AttendanceSummary"] = {
  cohort_id: "synthetic",
  timezone: "Europe/Madrid",
  date_from: null,
  date_to: null,
  rule: "Completa = 1; media = 0,5",
  items: [],
  cohort_totals: {
    suppressed: true,
    enrollments: null,
    min_group_size: 5,
    attended_days: null,
    late_days: null,
    justified_absence_days: null,
    unjustified_absence_days: null,
    unrecorded_days: null,
    attendance_rate: null,
  },
}
describe("server attendance totals", () => {
  it("keeps suppressed groups distinct from zero attendance", () => {
    const html = renderToStaticMarkup(<AttendanceTotals summary={base} />)
    expect(html).toContain("Agregado oculto")
    expect(html).toContain("No equivale a cero")
    expect(html).not.toContain("Asistidos: 0")
  })
  it("keeps half days, unrecorded sessions and null rates distinct", () => {
    const html = renderToStaticMarkup(
      <AttendanceTotals
        summary={{
          ...base,
          items: [
            {
              enrollment_id: "synthetic-person",
              held_days: 1,
              attended_days: 0.5,
              late_days: 0.5,
              attended_in_person_days: 0.5,
              attended_online_days: 0,
              justified_absence_days: 0,
              unjustified_absence_days: 0,
              unrecorded_days: 0.5,
              attendance_rate: null,
            },
          ],
        }}
      />,
    )
    expect(html).toContain("0.5")
    expect(html).toContain("Sin dato")
    expect(html).toContain("Sin registros")
    expect(html).not.toContain("0.0 %")
  })
  it("renders a real zero rate as zero rather than missing", () => {
    const item = {
      enrollment_id: "synthetic",
      held_days: 1,
      attended_days: 0,
      late_days: 0,
      attended_in_person_days: 0,
      attended_online_days: 0,
      justified_absence_days: 0,
      unjustified_absence_days: 1,
      unrecorded_days: 0,
      attendance_rate: 0,
    }
    const html = renderToStaticMarkup(
      <AttendanceTotals summary={{ ...base, items: [item] }} />,
    )
    expect(html).toContain("0.0 %")
    expect(html).not.toContain("Sin registros")
  })
})
