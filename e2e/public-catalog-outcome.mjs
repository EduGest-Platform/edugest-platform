/** Explicit expectations prevent a repeated registration from passing with a second receipt. */
export function expectedApplicationOutcome(value) {
  if (!['created', 'duplicate'].includes(value)) throw new Error('Set E2E_EXPECT_OUTCOME to created or duplicate')
  return value
}

export function matchesApplicationOutcome(expected, text) {
  const receipt = text.includes('Candidatura recibida')
  const duplicate = text.includes('Ya existe una candidatura')
  return expectedApplicationOutcome(expected) === 'created' ? receipt && !duplicate : duplicate && !receipt
}
