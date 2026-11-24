/** KAN-192: real HTTP journey on disposable local services, never direct application-stage writes. */
const origin = new URL(process.env.GISTAR_API ?? 'http://localhost:8000')
if (origin.protocol !== 'http:' || !['localhost', '127.0.0.1'].includes(origin.hostname) ||
    origin.username || origin.password || origin.pathname !== '/' || origin.search || origin.hash) {
  throw new Error('Local HTTP API origin required')
}
const password = process.env.GISTAR_DEMO_PASSWORD
if (!password) throw new Error('Synthetic demo password required')
const fixture = process.env.E2E_FIXTURE_ID ?? 'local-f2-admission'
if (!/^[a-zA-Z0-9-]{1,48}$/.test(fixture)) throw new Error('Invalid synthetic fixture identifier')
const email = `e2e.${fixture.toLowerCase()}@example.test`
const call = 'CONV-IA-2027A'
const cohort = 'COH-E2E-F2'
const reason = 'Synthetic human deliberation for the HTTP journey'
const contactText = 'Synthetic F2 preselection contact'

function check(ok, label) {
  if (!ok) throw new Error('F2 assertion failed')
  console.log(`PASS · ${label}`)
}

async function request(path, expected, { method = 'GET', token, body } = {}) {
  const response = await fetch(`${origin.origin}/api/v1${path}`, {
    method, redirect: 'error', signal: AbortSignal.timeout(10000),
    headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}), ...(body ? { 'Content-Type': 'application/json' } : {}) },
    ...(body ? { body: JSON.stringify(body) } : {}),
  })
  if (!(Array.isArray(expected) ? expected : [expected]).includes(response.status)) throw new Error('Unexpected F2 HTTP status')
  return { status: response.status, data: await response.json() }
}

async function login(email) {
  return (await request('/auth/login', 200, { method: 'POST', body: { email, password } })).data.access_token
}

try {
  const submitted = await request('/applications', [201, 409], { method: 'POST', body: {
    call_id: call, nombre: 'Persona F2 Sintética', email,
    motivacion: 'Motivación sintética para probar inscripción y matrícula.', disponibilidad: 'Flexible', acepta_datos_sinteticos: true,
  } })
  const recruiter = await login('captacion.ia@gistar.example')
  const selector = await login('seleccion.ia@gistar.example')
  const coordinator = await login('coordinacion@gistar.example')
  const admin = await login('admin@gistar.example')
  const list = (await request(`/applications?call_id=${call}&q=${encodeURIComponent(email)}`, 200, { token: recruiter })).data
  check(list.total === 1 && list.items.length === 1, 'Exactly one persisted intake')
  const target = list.items[0]
  const path = `/applications/${target.id}`
  const policy = (await request(`/calls/${call}/selection-policy`, 200, { token: selector })).data
  check(policy.selection_quorum === 2, 'Two-person selection policy is active')
  const vote = { decision: 'admitida', reason, cohort_id: cohort }

  if (submitted.status === 201) {
    check(submitted.data.id === target.id && target.stage === 'enviada', 'Public receipt matches persisted application')
    await request(`${path}/events`, 201, { method: 'POST', token: recruiter, body: {
      tipo: 'contacto', canal: 'telefono', resultado: 'respondida', resumen: contactText,
    } })
    const outsider = await login('captacion.data@gistar.example')
    await request(`${path}/events`, 403, { method: 'POST', token: outsider, body: { tipo: 'nota', resumen: 'Synthetic denied F2 note' } })
    const invited = (await request(`${path}/preselection-decisions`, 201, { method: 'POST', token: recruiter, body: { decision: 'convocada', reason } })).data
    check(invited.from_stage === 'enviada' && invited.to_stage === 'convocada', 'Human preselection invitation persisted')
    const first = (await request(`${path}/selection-decisions`, 202, { method: 'POST', token: selector, body: vote })).data
    check(first.state === 'pending' && first.quorum === 2 && first.votes.length === 1, 'One human approval remains pending')
    const pending = (await request(`${path}/selection-decisions`, 200, { token: selector })).data
    check(pending.items.length === 0 && pending.pending_votes.length === 1, 'No applied admission before quorum')
    const repeated = (await request(`${path}/selection-decisions`, 409, { method: 'POST', token: selector, body: vote })).data
    check(repeated.code === 'already_approved', 'Same person cannot satisfy the quorum twice')
    const applied = (await request(`${path}/selection-decisions`, 201, { method: 'POST', token: coordinator, body: vote })).data
    check(applied.decision === 'admitida' && applied.cohort_id === cohort && !!applied.enrollment_id, 'Second distinct person admits and enrolls')
  } else {
    check(target.stage === 'admitida', 'Repeat-run fixture remains admitted')
  }

  const history = (await request(`${path}/selection-decisions`, 200, { token: selector })).data
  check(history.items.length === 1 && history.pending_votes.length === 0, 'Exactly one applied decision remains')
  const decision = history.items[0]
  check(decision.decision === 'admitida' && decision.cohort_id === cohort && !!decision.enrollment_id, 'Applied history retains cohort and enrollment identity')
  const enrollment = (await request(`/enrollments/${decision.enrollment_id}/submissions`, 200, { token: admin })).data
  check(enrollment.enrollment_id === decision.enrollment_id && enrollment.cohort_id === cohort, 'Independent academic endpoint resolves persisted enrollment')
  const duplicate = (await request(`${path}/selection-decisions`, 409, { method: 'POST', token: selector, body: vote })).data
  check(duplicate.code === 'selection_ended', 'Closed selection rejects another admission')
  const after = (await request(`${path}/selection-decisions`, 200, { token: selector })).data
  check(after.items.length === 1 && after.items[0].enrollment_id === decision.enrollment_id, 'Rejected duplicate preserves enrollment')
  const dossier = (await request(path, 200, { token: selector })).data
  check(dossier.stage === 'admitida' && dossier.events.filter(e => e.tipo === 'contacto' && e.resumen === contactText).length === 1,
    'CRM contact survives the complete journey without duplication')
  check(dossier.events.every(e => e.resumen !== 'Synthetic denied F2 note'), 'Denied foreign-program write left no CRM note')
  console.log('PASS · F2 HTTP admission-to-enrollment journey')
} catch {
  // Never print bodies, exception text, tokens, credentials, names or email addresses.
  console.error('FAIL · F2 HTTP admission-to-enrollment journey')
  process.exitCode = 1
}
