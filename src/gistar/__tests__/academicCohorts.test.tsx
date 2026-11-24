import { describe, expect, it } from "vitest"
import { renderToStaticMarkup } from "react-dom/server"
import { CohortDetails, type AcademicCohort } from "../views/api/ApiCohorts"

const cohort: AcademicCohort = {
  id: "synthetic",
  program_id: "P-IA",
  nombre: "Cohorte sintética",
  inicio: "2026-01-01",
  fin: "2026-12-01",
  timezone: "Europe/Madrid",
  can_record_attendance: false,
}
describe("authorized cohort details", () => {
  it("shows dates and timezone without offering recording to aggregate readers", () => {
    const html = renderToStaticMarkup(<CohortDetails cohort={cohort} />)
    expect(html).toContain("2026-01-01")
    expect(html).toContain("Europe/Madrid")
    expect(html).toContain("Solo consulta de agregados")
    expect(html).not.toContain("Puede registrar")
  })
})
