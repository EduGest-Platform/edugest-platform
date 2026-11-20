import { describe, expect, it } from "vitest"

import type { Schemas } from "../../shared/api/client"

import {
  requirementGroups,
  requirementSnapshot,
} from "../views/api/requirementData"

import { summarizeReview } from "../requirements"

type Definition = Schemas["CallRequirementOut"]

type Review = Schemas["RequirementReviewOut"]

const definition = (overrides: Partial<Definition> = {}): Definition => ({
  id: "definition-1",
  call_id: "synthetic-call",
  ref: "synthetic-v1",
  code: "synthetic",
  version: 1,

  label: "Synthetic requirement",
  kind: "required",
  funder: "Do not copy to the panel",
  created_at: "2026-11-20T12:00:00Z",
  ...overrides,
})

const review = (overrides: Partial<Review> = {}): Review => ({
  id: "review-1",
  application_id: "synthetic-app",
  requirement_ref: "synthetic-v1",
  requirement_definition_id: "definition-1",

  result: "met",
  reviewer: "Synthetic reviewer",
  reviewed_at: "2026-11-20T12:00:00Z",
  reason: "Synthetic reason",
  version: 1,
  ...overrides,
})

describe("server requirement projection", () => {
  it("keeps an empty catalogue and missing reviews unreviewed", () => {
    expect(requirementSnapshot([], [], {}).checks).toEqual([])

    const snapshot = requirementSnapshot([definition()], [], {})

    expect(snapshot.checks[0].status).toBe("pendiente")

    expect(summarizeReview(snapshot.checks).state).toBe("sin_revisar")
  })

  it.each([
    ["pending", "pendiente"],
    ["met", "cumple"],
    ["not_met", "no_cumple"],

    ["exception_under_review", "excepcion_en_revision"],
    ["exception_approved", "excepcion_aprobada"],
  ] as const)(
    "maps %s to %s while preserving human review context",
    (result, expected) => {
      const snapshot = requirementSnapshot(
        [definition()],
        [review({ result })],
        {},
      )

      expect(snapshot.checks[0]).toMatchObject({
        status: expected,
        reviewedBy: "Synthetic reviewer",
        note: "Synthetic reason",
      })

      expect(JSON.stringify(snapshot)).not.toContain("Do not copy to the panel")
    },
  )

  it("does not trust legacy, mismatched or foreign-definition reviews", () => {
    for (const requirement_definition_id of [
      null,
      undefined,
      "another-definition",
    ]) {
      const snapshot = requirementSnapshot(
        [definition()],
        [review({ requirement_definition_id })],
        {},
      )

      expect(snapshot.checks[0]).toMatchObject({
        status: "pendiente",
        reviewedBy: undefined,
        note: undefined,
      })

      expect(snapshot.unverifiedReviews).toBe(1)
    }

    const mismatched = requirementSnapshot(
      [definition()],
      [review({ requirement_ref: "different-ref" })],
      {},
    )

    expect(mismatched.checks[0].status).toBe("pendiente")
  })

  it("requires explicit choice between versions, never latest or whichever has a good review", () => {
    const versions = [
      definition(),
      definition({ id: "definition-2", ref: "synthetic-v2", version: 2 }),
    ]

    expect(requirementSnapshot(versions, [review()], {})).toMatchObject({
      checks: [],
      unresolvedCodes: ["synthetic"],
    })

    expect(
      requirementSnapshot(versions, [review()], { synthetic: "synthetic-v1" })
        .checks[0].status,
    ).toBe("cumple")

    expect(
      requirementSnapshot(versions, [review()], { synthetic: "synthetic-v2" })
        .checks[0].status,
    ).toBe("pendiente")

    expect(
      requirementSnapshot(versions, [review()], {
        synthetic: "unknown-version",
      }).unresolvedCodes,
    ).toEqual(["synthetic"])
  })

  it("keeps required and recommended meanings and never creates an admission decision", () => {
    const required = requirementSnapshot(
      [definition()],
      [review({ result: "not_met" })],
      {},
    )

    expect(summarizeReview(required.checks).state).toBe(
      "necesita_decision_humana",
    )

    const recommended = requirementSnapshot(
      [definition({ kind: "recommended" })],
      [review({ result: "not_met" })],
      {},
    )

    expect(recommended.checks[0].kind).toBe("recomendado")

    expect(summarizeReview(recommended.checks).openIssues).toBe(0)
  })

  it("groups deterministically without mutating the server catalogue", () => {
    const definitions = [
      definition({ id: "definition-2", ref: "synthetic-v2", version: 2 }),
      definition(),
    ]

    const original = structuredClone(definitions)

    expect(
      requirementGroups(definitions)[0].versions.map((row) => row.version),
    ).toEqual([1, 2])

    expect(definitions).toEqual(original)
  })
})
