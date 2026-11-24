import { describe, expect, it } from "vitest"
import { renderToStaticMarkup } from "react-dom/server"
import { SelectionEvidence } from "../views/api/ServerSelection"
import type { Schemas } from "../../shared/api/client"

describe("selection evidence", () => {
  it("does not invent votes or historical quorum for an empty history", () => {
    const html = renderToStaticMarkup(
      <SelectionEvidence
        history={{
          application_id: "synthetic",
          quorum: 3,
          items: [],
          pending_votes: [],
        }}
      />,
    )
    expect(html).toContain("Quórum actual: 3")
    expect(html).toContain("No hay votos pendientes")
    expect(html).toContain("No hay decisiones aplicadas")
    expect(html).toContain("No reconstruye la política histórica")
  })
  it("retains disagreeing votes and escapes operational reasons", () => {
    const vote = {
      decision: "admitida" as const,
      cohort_id: "synthetic",
      reason: "<script>private</script>",
      actor: "Persona sintética",
      occurred_at: "2026-11-24T10:00:00Z",
    }
    const history: Schemas["SelectionDecisionList"] = {
      application_id: "synthetic",
      quorum: 2,
      pending_votes: [vote],
      items: [
        {
          id: "decision",
          application_id: "synthetic",
          decision: "lista_espera",
          from_stage: "convocada",
          to_stage: "lista_espera",
          reason: "Revisión humana",
          actor: null,
          occurred_at: vote.occurred_at,
          cohort_id: null,
          enrollment_id: null,
          votes: [vote, { ...vote, decision: "lista_espera" }],
        },
      ],
    }
    const html = renderToStaticMarkup(<SelectionEvidence history={history} />)
    expect(html).toContain("admitida")
    expect(html).toContain("lista_espera")
    expect(html).toContain("&lt;script&gt;")
    expect(html).not.toContain("<script>")
    expect(html).not.toContain("Sin evidencia de votos vinculada")
  })
})
