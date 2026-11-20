import type { Schemas } from "../../../shared/api/client"

import type { RequirementCheck, RequirementStatus } from "../../requirements"

type Definition = Schemas["CallRequirementOut"]

type Review = Schemas["RequirementReviewOut"]

const STATUS: Record<Review["result"], RequirementStatus> = {
  pending: "pendiente",
  met: "cumple",
  not_met: "no_cumple",

  exception_under_review: "excepcion_en_revision",
  exception_approved: "excepcion_aprobada",
}

export function requirementGroups(definitions: readonly Definition[]) {
  const groups = new Map<string, Definition[]>()

  for (const definition of definitions) {
    const group = groups.get(definition.code) ?? []

    group.push(definition)

    groups.set(definition.code, group)
  }

  return [...groups.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([code, versions]) => ({
      code,
      versions: [...versions].sort((a, b) => a.version - b.version),
    }))
}

/** A single configured version is unambiguous; multiple versions need an explicit display choice. */

export function requirementSnapshot(
  definitions: readonly Definition[],
  reviews: readonly Review[],
  choices: Record<string, string>,
) {
  const checks: RequirementCheck[] = []

  const unresolvedCodes: string[] = []

  for (const { code, versions } of requirementGroups(definitions)) {
    const selected =
      versions.length === 1
        ? versions[0]
        : versions.find((row) => row.ref === choices[code])

    if (!selected) {
      unresolvedCodes.push(code)

      continue
    }

    const review = reviews.find(
      (row) =>
        row.requirement_ref === selected.ref &&
        row.requirement_definition_id === selected.id,
    )

    checks.push({
      id: selected.ref,
      label: `${selected.label} · v${selected.version}`,

      kind: selected.kind === "required" ? "obligatorio" : "recomendado",

      status: review ? STATUS[review.result] : "pendiente",

      note: review?.reason,
      reviewedBy: review?.reviewer,
      reviewedAt: review?.reviewed_at,
    })
  }

  const unverifiedReviews = reviews.filter(
    (review) =>
      !definitions.some(
        (definition) =>
          review.requirement_ref === definition.ref &&
          review.requirement_definition_id === definition.id,
      ),
  ).length

  return { checks, unresolvedCodes, unverifiedReviews }
}
