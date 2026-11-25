/** KAN-112 / KAN-132: public intake through an explicit campaign requirement review. */
import { randomUUID } from 'node:crypto'

const origin = new URL(process.env.GISTAR_API ?? 'http://localhost:8000')
if (origin.protocol !== 'http:' || !['localhost', '127.0.0.1'].includes(origin.hostname) ||
    origin.username || origin.password || origin.pathname !== '/' || origin.search || origin.hash) {
  throw new Error('Local synthetic HTTP origin required')
}
const password = process.env.GISTAR_DEMO_PASSWORD
if (!password) throw new Error('Set the synthetic demo password')

const call = 'CONV-IA-2027A'
const fixture = randomUUID()
const reference = `intake-${fixture}`

async function request(path, expected, { method = 'GET', token, body } = {}) {
  const response = await fetch(`${origin.origin}/api/v1${path}`, {
    method, redirect: 'error', signal: AbortSignal.timeout(10000),
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(body ? { 'Content-Type': 'application/json' } : {}),
    },
    ...(body ? { body: JSON.stringify(body) } : {}),
  })
  const allowed = Array.isArray(expected) ? expected : [expected]
  if (!allowed.includes(response.status)) throw new Error('Unexpected HTTP status')
  return { status: response.status, data: await response.json() }
}

async function login(email) {
  return (await request('/auth/login', 200, { method: 'POST', body: { email, password } })).data.access_token
}

function check(condition, label) {
  if (!condition) throw new Error(label)
  console.log(`PASS · ${label}`)
}

try {
  const admin = await login('admin@gistar.example')
  const selector = await login('seleccion.ia@gistar.example')
  const outsider = await login('captacion.data@gistar.example')
  const offer = (await request(`/public/courses/${call}`, 200)).data
  check(offer.id === call && offer.admission_state === 'abierta', 'Published offer is open for public applications')
  const definition = (await request(`/calls/${call}/requirements`, 201, {
    method: 'POST', token: admin, body: {
      ref: reference, code: reference, kind: 'required', label: 'Comprobación sintética de disponibilidad',
    },
  })).data
  check(definition.ref === reference && definition.version === 1, 'Campaign has a versioned mandatory requirement')

  const email = `intake.${fixture}@example.test`
  const payload = {
    call_id: call, nombre: 'Persona sintética de registro', email, disponibilidad: 'Flexible',
    motivacion: 'Solicitud sintética para probar la revisión humana de requisitos.',
    acepta_datos_sinteticos: true, requirement_result: 'met',
  }
  const invalid = (await request('/applications', 422, {
    method: 'POST', body: { ...payload, acepta_datos_sinteticos: 1 },
  })).data
  check(invalid.detail.some(issue => issue.loc.at(-1) === 'acepta_datos_sinteticos'), 'Numeric acknowledgement is rejected')
  const submissions = await Promise.all([
    request('/applications', [201, 409], { method: 'POST', body: payload }),
    request('/applications', [201, 409], { method: 'POST', body: { ...payload, email: email.toUpperCase() } }),
  ])
  check(submissions.map(result => result.status).sort().join(',') === '201,409', 'A concurrent resend creates only one application')
  const receipt = submissions.find(result => result.status === 201).data
  check(receipt.stage === 'enviada', 'Mandatory requirement does not exclude the applicant on submission')

  const target = `/applications/${receipt.id}`
  const reviews = `${target}/requirement-reviews`
  const preview = () => request(`${target}/requirement-prefilter`, 200, {
    method: 'POST', token: selector, body: { requirement_refs: [reference] },
  })
  const before = (await request(reviews, 200, { token: selector })).data
  check(before.items.length === 0, 'Public intake cannot record or approve its own requirement review')
  const pending = (await preview()).data
  check(pending.items[0].result === 'pending' && pending.unresolved_required_refs.includes(reference) &&
    pending.proposed_action === 'human_review', 'Pending mandatory requirement proposes human review')
  await request(reviews, 403, { token: outsider })
  check(true, 'Another programme cannot read the applicant’s requirement reviews')

  const review = `${reviews}/${reference}`
  const record = (result, expectedVersion, expected) => request(review, expected, {
    method: 'PUT', token: admin, body: {
      result, expected_version: expectedVersion, reason: 'Revisión humana sintética para la prueba',
    },
  })
  await record('not_met', undefined, 201)
  await record('exception_under_review', 1, 200)
  const exceptional = (await preview()).data
  check(exceptional.items[0].result === 'exception_under_review' && exceptional.proposed_action === 'human_review',
    'An exception under human review still needs a decision')
  await record('exception_approved', 2, 200)
  const approved = (await preview()).data
  check(approved.items[0].result === 'exception_approved' && approved.items[0].verified_review &&
    !approved.unresolved_required_refs.includes(reference), 'Explicit human approval resolves the selected requirement')
  const dossier = (await request(target, 200, { token: selector })).data
  check(dossier.stage === 'enviada' && dossier.events.filter(event => event.tipo === 'creada').length === 1,
    'The dossier retains one creation event and its original stage')
} catch {
  console.error('FAIL · HTTP public intake and human requirement review')
  process.exitCode = 1
}
