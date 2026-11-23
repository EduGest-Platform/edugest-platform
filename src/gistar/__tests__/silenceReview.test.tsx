import { describe, expect, it, vi } from "vitest"
import { renderToStaticMarkup } from "react-dom/server"
import type { Schemas } from "../../shared/api/client"
import { SilenceAlertList } from "../views/api/ServerSilenceReview"

const item = (
  evidence: Partial<Schemas["SilenceEvidence"]> = {},
): Schemas["SilenceReviewItem"] => ({
  application_id: "synthetic-application",
  codigo: "SYN-0001",
  display_name: "Persona Sintética",
  stage: "enviada",
  evidence: {
    unanswered_attempts: 2,
    last_attempt_at: null,
    days_without_response: null,
    silence_days: 30,
    silence_max_contacts: 4,
    silence_warning_contacts: 2,
    alert_level: "leve",
    threshold_met: false,
    ...evidence,
  },
})

describe("server silence evidence presentation", () => {
  it("shows an empty response without inventing alerts", () => {
    expect(
      renderToStaticMarkup(
        <SilenceAlertList items={[]} onOpen={() => undefined} />,
      ),
    ).toContain("No hay alertas de silencio")
  })
  it("shows an early warning without converting missing dates to zero days", () => {
    const open = vi.fn()
    const html = renderToStaticMarkup(
      <SilenceAlertList items={[item()]} onOpen={open} />,
    )
    expect(html).toContain("Aviso temprano de contacto")
    expect(html).toContain("sin fecha confirmada")
    expect(html).not.toContain("0 días sin respuesta")
    expect(html).toContain("No se cumple el umbral de acción")
    expect(html).toContain("Abrir expediente")
    expect(open).not.toHaveBeenCalled()
  })
  it("uses the server action flag and displays configured thresholds without applying a new rule", () => {
    const html = renderToStaticMarkup(
      <SilenceAlertList
        items={[
          item({
            alert_level: "accion",
            threshold_met: true,
            silence_days: 5,
            silence_max_contacts: 3,
            unanswered_attempts: 3,
            days_without_response: 6,
            last_attempt_at: "2026-11-17T12:00:00Z",
          }),
        ]}
        onOpen={() => undefined}
      />,
    )
    expect(html).toContain("Revisión por plazo y contactos")
    expect(html).toContain("3 intentos y 5 días")
    expect(html).toContain("revisión humana")
    expect(html).toContain("6 días sin respuesta")
    expect(html).not.toContain("Confirmar silencio")
  })
  it("escapes the display name rather than rendering executable markup", () => {
    const value = { ...item(), display_name: "<img src=x onerror=alert(1)>" }
    const html = renderToStaticMarkup(
      <SilenceAlertList items={[value]} onOpen={() => undefined} />,
    )
    expect(html).toContain("&lt;img")
    expect(html).not.toContain("<img")
  })
})
