/** KAN-49: waitlist through human promotion and the applicant's own outcome. */
const origin = new URL(process.env.GISTAR_API ?? 'http://localhost:8000')
if (origin.protocol !== 'http:' || !['localhost', '127.0.0.1'].includes(origin.hostname) ||
    origin.username || origin.password || origin.pathname !== '/' || origin.search || origin.hash) {
  throw new Error('Local synthetic HTTP origin required')
}
const password = process.env.GISTAR_DEMO_PASSWORD
if (!password) throw new Error('Set the synthetic demo password')

const email = 'f2.waitlist.owner@example.test'
const call = 'CONV-IA-2027A'
const cohort = 'COH-E2E-F2'
const reason = 'Synthetic internal deliberation for the waitlist journey'

async function request(path, expected, { method = 'GET', token, body } = {}) {
  const response = await fetch(`${origin.origin}/api/v1${path}`, {
    method, redirect: 'error', signal: AbortSignal.timeout(10000),
    headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}), ...(body ? { 'Content-Type': 'application/json' } : {}) },
    ...(body ? { body: JSON.stringify(body) } : {}),
  })
  const allowed = Array.isArray(expected) ? expected : [expected]
  if (!allowed.includes(response.status)) throw new Error('Unexpected HTTP status')
  return { status: response.status, data: await response.json() }
}

async function login(address) {
  return (await request('/auth/login', 200, { method: 'POST', body: { email: address, password } })).data.access_token
}

function check(condition, label) {
  if (!condition) throw new Error(label)
  console.log(`PASS · ${label}`)
}

async function checkQueue(selector, applicationId, expected) {
  const overview = (await request(`/calls/${call}/selection-overview`, 200, { token: selector })).data
  check(overview.waiting_list.some(row => row.application_id === applicationId) === expected,
    expected ? 'Staff queue includes the waiting applicant' : 'Staff queue removes the promoted applicant')
}

try {
  // The applicant applies signed in: an anonymous application is never linked to an account on its own (KAN-274).
  const owner = await login(email)
  const submitted = await request('/applications', [201, 409], { method: 'POST', token: owner, body: {
    call_id: call, nombre: 'Persona sintética en lista de espera', email,
    motivacion: 'Motivación sintética para verificar la promoción y la matrícula.', disponibilidad: 'Flexible', acepta_datos_sinteticos: true,
  } })
  const selector = await login('seleccion.ia@gistar.example')
  const coordinator = await login('coordinacion@gistar.example')
  const applications = (await request('/me/applications', 200, { token: owner })).data.filter(row => row.call_id === call)
  check(applications.length === 1, 'One application is linked to the applicant account')
  const applicationId = applications[0].id
  const ownPath = `/me/applications/${applicationId}/selection-outcome`
  const staffPath = `/applications/${applicationId}/selection-decisions`
  const admission = { decision: 'admitida', cohort_id: cohort, reason }

  if (submitted.status === 201) {
    const recruiter = await login('captacion.ia@gistar.example')
    await request(`/applications/${applicationId}/preselection-decisions`, 201, {
      method: 'POST', token: recruiter, body: { decision: 'convocada', reason },
    })
    const waiting = { decision: 'lista_espera', reason }
    await request(staffPath, 202, { method: 'POST', token: selector, body: waiting })
    const pending = (await request(ownPath, 200, { token: owner })).data
    check(pending.outcome === null && pending.enrollment === null, 'One waitlist signature exposes no applied decision')
    await request(staffPath, 201, { method: 'POST', token: coordinator, body: waiting })
    await checkQueue(selector, applicationId, true)
    const queued = (await request(ownPath, 200, { token: owner })).data
    check(queued.outcome === 'lista_espera' && queued.enrollment === null, 'Waitlisted applicant has no enrollment')
    await request(staffPath, 202, { method: 'POST', token: selector, body: admission })
    const promoting = (await request(ownPath, 200, { token: owner })).data
    check(promoting.outcome === queued.outcome && promoting.decided_at === queued.decided_at && promoting.enrollment === null,
      'One promotion signature preserves the applied waitlist outcome')
    await request(staffPath, 201, { method: 'POST', token: coordinator, body: admission })
  }

  const history = (await request(staffPath, 200, { token: selector })).data
  check(history.items.length === 2 && history.items[0].decision === 'lista_espera' && history.items[1].decision === 'admitida',
    'Staff history preserves the two applied human decisions')
  const promotion = history.items[1]
  const published = (await request(ownPath, 200, { token: owner })).data
  const fields = ['application_id', 'decided_at', 'enrollment', 'outcome', 'stage']
  check(Object.keys(published).sort().join(',') === fields.join(',') && published.outcome === 'admitida' &&
    published.enrollment?.enrollment_id === promotion.enrollment_id && published.enrollment?.cohort_id === cohort &&
    published.enrollment?.status === 'activa', 'Applicant receives only the verified own enrollment and outcome')
  const submissions = (await request(`/enrollments/${published.enrollment.enrollment_id}/submissions`, 200, { token: owner })).data
  check(submissions.enrollment_id === published.enrollment.enrollment_id, 'The same account can use its existing academic read route')
  await checkQueue(selector, applicationId, false)
  const duplicate = (await request(staffPath, 409, { method: 'POST', token: selector, body: admission })).data
  check(duplicate.code === 'selection_ended', 'Another signature cannot repeat the promotion')
  const other = await login('aspirante-01@example.test')
  await request(ownPath, 404, { token: other })
  check(true, 'Another applicant cannot read the outcome')
  const again = (await request(ownPath, 200, { token: owner })).data
  check(again.enrollment?.enrollment_id === published.enrollment.enrollment_id, 'Repeat reads preserve enrollment identity')
} catch {
  console.error('FAIL · HTTP waitlist-to-enrollment journey')
  process.exitCode = 1
}
