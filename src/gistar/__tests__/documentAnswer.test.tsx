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
})
