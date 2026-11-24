import { describe, expect, it } from "vitest"
import { renderToStaticMarkup } from "react-dom/server"
import type { Schemas } from "../../shared/api/client"
import { DocumentAnswer } from "../views/api/ApiAssistant"

const answer: Schemas["AskOut"] = {
  status: "answered",
  mode: "extractive",
  retrieval: "keyword",
  answer: "<script>unsafe</script>",
  citations: [
    {
      source_key: "synthetic",
      title: "Guía sintética",
      version: "v1",
      valid_from: "2026-01-01",
      valid_until: null,
      excerpt: "<img src=x onerror=alert(1)>",
    },
  ],
  as_of: "2026-11-24",
  scope_cohorts: ["COH-IA"],
  source_kind: "documents",
  record: null,
}
describe("documental API answers", () => {
  it("shows source version, validity and actual retrieval method as text", () => {
    const html = renderToStaticMarkup(<DocumentAnswer result={answer} />)
    expect(html).toContain("Guía sintética")
    expect(html).toContain("v1")
    expect(html).toContain("2026-01-01")
    expect(html).toContain("por palabras")
    expect(html).toContain("2026-11-24")
    expect(html).toContain("&lt;script&gt;")
    expect(html).not.toContain("<script>")
    expect(html).not.toContain("<img")
  })
  it("does not render an answer or citations when the server abstains", () => {
    const html = renderToStaticMarkup(
      <DocumentAnswer result={{ ...answer, status: "no_source" }} />,
    )
    expect(html).toContain("No consta")
    expect(html).not.toContain("Guía sintética")
    expect(html).not.toContain("unsafe")
  })
  it("warns when an answered result has no citation", () => {
    const html = renderToStaticMarkup(
      <DocumentAnswer result={{ ...answer, citations: [] }} />,
    )
    expect(html).toContain("No la uses como evidencia documental")
  })
  it("shows records answers with tool, source and time instead of citations", () => {
    const html = renderToStaticMarkup(
      <DocumentAnswer
        result={{
          ...answer,
          mode: "template",
          retrieval: null,
          citations: [],
          source_kind: "records",
          answer: "Asistencia en COH-IA hasta hoy (en días): asistidos 1",
          record: {
            tool: "get_attendance_summary",
            source: "attendance_session, attendance_record",
            rule: "Día completo = 1",
            generated_at: "2026-11-24T10:00:00Z",
            aggregate_only: false,
          },
        }}
      />,
    )
    expect(html).toContain("asistidos 1")
    expect(html).toContain("get_attendance_summary")
    expect(html).toContain("2026-11-24T10:00:00Z")
    expect(html).not.toContain("No la uses como evidencia documental")
  })
  it("keeps the server text when records have no data", () => {
    const html = renderToStaticMarkup(
      <DocumentAnswer
        result={{
          ...answer,
          status: "no_source",
          mode: "template",
          retrieval: null,
          citations: [],
          source_kind: "records",
          record: null,
          answer: "No hay registros de asistencia en COH-DATA para ese periodo.",
        }}
      />,
    )
    expect(html).toContain("No hay registros")
    expect(html).not.toContain("No consta")
  })
})
