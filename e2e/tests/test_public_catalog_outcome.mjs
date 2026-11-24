import { test } from 'node:test'
import assert from 'node:assert/strict'
import { expectedApplicationOutcome, matchesApplicationOutcome } from '../public-catalog-outcome.mjs'

test('first execution requires a receipt and rejects a duplicate response', () => {
  assert.equal(matchesApplicationOutcome('created', 'Candidatura recibida con el código SYNTH-0001'), true)
  assert.equal(matchesApplicationOutcome('created', 'Ya existe una candidatura con este correo'), false)
})

test('repeat execution requires rejection and fails on a second receipt', () => {
  assert.equal(matchesApplicationOutcome('duplicate', 'Ya existe una candidatura con este correo'), true)
  assert.equal(matchesApplicationOutcome('duplicate', 'Candidatura recibida con el código SYNTH-0002'), false)
})

test('ambiguous or missing results never satisfy either expectation', () => {
  for (const expected of ['created', 'duplicate']) {
    assert.equal(matchesApplicationOutcome(expected, 'Candidatura recibida. Ya existe una candidatura.'), false)
    assert.equal(matchesApplicationOutcome(expected, 'Enviando…'), false)
  }
})

test('missing and misspelled expectations fail before browser startup', () => {
  for (const value of [undefined, '', 'success', 'duplicated']) assert.throws(() => expectedApplicationOutcome(value))
  assert.equal(expectedApplicationOutcome('created'), 'created')
  assert.equal(expectedApplicationOutcome('duplicate'), 'duplicate')
})
