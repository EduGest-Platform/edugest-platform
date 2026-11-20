import { useEffect, useState } from "react"

import { api, type Schemas } from "../../../shared/api/client"

import { describeApiError, problemText } from "../../../shared/api/errors"

import { RequirementReviewPanel } from "../../components/RequirementReviewPanel"

import { Button, Field, Notice, inputCls } from "../../ui"

import { requirementGroups, requirementSnapshot } from "./requirementData"

type Data = {
  definitions: Schemas["CallRequirementOut"][]
  reviews: Schemas["RequirementReviewOut"][]
}

export function ServerRequirementReview({
  applicationId,
  callId,
}: {
  applicationId: string
  callId: string
}) {
  const [state, setState] = useState<{
    scope: string
    data?: Data
    error?: string
  } | null>(null)

  const [refresh, setRefresh] = useState(0)

  const [choices, setChoices] = useState<Record<string, string>>({})

  const scope = `${callId}:${applicationId}`

  useEffect(() => {
    const controller = new AbortController()

    let active = true

    setState(null)

    setChoices({})

    async function load() {
      try {
        const [catalogue, history] = await Promise.all([
          api.GET("/api/v1/calls/{call_id}/requirements", {
            params: { path: { call_id: callId } },
            signal: controller.signal,
          }),

          api.GET("/api/v1/applications/{application_id}/requirement-reviews", {
            params: { path: { application_id: applicationId } },
            signal: controller.signal,
          }),
        ])

        if (!active) return

        for (const result of [catalogue, history]) {
          if (!result.data) {
            setState({
              scope,
              error: problemText(
                describeApiError(result.response.status, result.error),
              ),
            })

            return
          }
        }

        if (
          !catalogue.data ||
          !history.data ||
          catalogue.data.call_id !== callId ||
          history.data.application_id !== applicationId
        ) {
          setState({
            scope,
            error:
              "Los datos no corresponden a este expediente. Vuelve a actualizar.",
          })

          return
        }

        setState({
          scope,
          data: {
            definitions: catalogue.data.items,
            reviews: history.data.items,
          },
        })
      } catch {
        if (active)
          setState({
            scope,
            error:
              "No se ha podido consultar la revisión de requisitos. Inténtalo de nuevo.",
          })
      }
    }

    void load()

    return () => {
      active = false
      controller.abort()
    }
  }, [applicationId, callId, scope, refresh])

  const current = state?.scope === scope ? state : null

  const data = current?.data

  const snapshot = data
    ? requirementSnapshot(data.definitions, data.reviews, choices)
    : null

  return (
    <section
      data-server-requirements
      aria-label="Requisitos del servidor"
      className="grid gap-3"
    >
      <div className="flex items-center justify-between gap-2">
        <h3 className="font-semibold">Requisitos del servidor</h3>
        <Button
          size="sm"
          variant="ghost"
          onClick={() => setRefresh((value) => value + 1)}
          aria-label="Actualizar requisitos"
        >
          Actualizar requisitos
        </Button>
      </div>
      {!current && <p role="status">Cargando requisitos…</p>}
      {current?.error && (
        <Notice tone="warning" live="assertive">
          {current.error}
        </Notice>
      )}
      {data && snapshot && (
        <>
          {requirementGroups(data.definitions)
            .filter((group) => group.versions.length > 1)
            .map(({ code, versions }) => (
              <Field
                key={code}
                htmlFor={`requirement-version-${code}`}
                label={`Versión de ${code}`}
              >
                <select
                  id={`requirement-version-${code}`}
                  className={inputCls}
                  value={choices[code] ?? ""}
                  onChange={(event) =>
                    setChoices((previous) => ({
                      ...previous,
                      [code]: event.target.value,
                    }))
                  }
                >
                  <option value="">Elige una versión para consultar</option>
                  {versions.map((definition) => (
                    <option key={definition.ref} value={definition.ref}>
                      {definition.label} · v{definition.version}
                    </option>
                  ))}
                </select>
              </Field>
            ))}
          {snapshot.unresolvedCodes.length > 0 ? (
            <Notice>
              Elige una versión de cada requisito para consultar su estado. Esta
              elección no activa versiones ni modifica la candidatura.
            </Notice>
          ) : (
            <RequirementReviewPanel checks={snapshot.checks} source="server" />
          )}
          {snapshot.unverifiedReviews > 0 && (
            <Notice tone="warning">
              Hay revisiones sin una definición verificable. No se usan para
              afirmar que los requisitos se cumplen.
            </Notice>
          )}
          <p className="text-xs text-muted">
            Consulta de solo lectura de las versiones mostradas. No es una
            decisión de admisión ni ejecuta el prefiltro.
          </p>
        </>
      )}
    </section>
  )
}
