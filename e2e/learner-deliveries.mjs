/** KAN-56 / KAN-234: own deliveries and immutable reviewed submissions in API mode. */
import { randomUUID } from 'node:crypto'

const web = new URL(process.env.WEB_URL ?? 'http://localhost:8443/')
const api = new URL(process.env.GISTAR_API ?? 'http://localhost:8000')
for (const url of [web, api]) {
  if (url.protocol !== 'http:' || !['localhost', '127.0.0.1'].includes(url.hostname) ||
      url.username || url.password || url.pathname !== '/' || url.search || url.hash) {
    throw new Error('Local synthetic HTTP origins required')
  }
}
const password = process.env.GISTAR_DEMO_PASSWORD
if (!password) throw new Error('Set the synthetic demo password')

const { newBrowser, check, errors, finish, sleep } = await import('./cdp.mjs')
const suffix = randomUUID().slice(0, 8)
const title = `Entrega E2E abierta ${suffix}`
const overdueTitle = `Entrega E2E vencida ${suffix}`
const draftTitle = `Entrega E2E borrador ${suffix}`
const foreignTitle = `Entrega E2E otra cohorte ${suffix}`
const card = `[...document.querySelectorAll('main section')].find(item => item.querySelector('h2')?.textContent === ${JSON.stringify(title)})`

function requireCheck(label, result) {
  check(label, Boolean(result))
  if (!result) throw new Error('Learner delivery assertion failed')
}

async function waitFor(page, expression) {
  for (let attempt = 0; attempt < 50; attempt++) {
    if (await page.ev(expression)) return true
    await sleep(200)
  }
  return false
}

async function request(path, expected, { token, method = 'GET', body } = {}) {
  const response = await fetch(new URL(`/api/v1${path}`, api), {
    method, redirect: 'error', signal: AbortSignal.timeout(10000),
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(body ? { 'Content-Type': 'application/json' } : {}),
    },
    ...(body ? { body: JSON.stringify(body) } : {}),
  })
  if (response.status !== expected) throw new Error('Unexpected fixture HTTP status')
  return response.json()
}

async function login(email) {
  return (await request('/auth/login', 200, { method: 'POST', body: { email, password } })).access_token
}

async function makeAssignment(teacher, cohort, activityTitle, dayOffset, status = 'published') {
  return request(`/cohorts/${cohort}/assignments`, 201, {
    method: 'POST', token: teacher, body: {
      title: activityTitle, due_at: new Date(Date.now() + dayOffset * 86_400_000).toISOString(), status,
    },
  })
}

async function setPortfolio(page, value) {
  const id = await page.ev(`(${card})?.querySelector('input[type=url]')?.id`)
  return id && await page.set(`[id=${JSON.stringify(id)}]`, value)
}

try {
  const teacher = await login('docente@gistar.example')
  const learner = await login('coder-01@example.test')
  const reader = await login('captacion.data@gistar.example')
  const enrollment = (await request('/me/enrollments', 200, { token: learner })).items.find(item => item.status === 'activa')
  requireCheck('Coder has one selected active enrollment', enrollment?.cohort_id === 'COH-IA')
  const assignment = await makeAssignment(teacher, enrollment.cohort_id, title, 3)
  await makeAssignment(teacher, enrollment.cohort_id, overdueTitle, -3)
  await makeAssignment(teacher, enrollment.cohort_id, draftTitle, 3, 'draft')
  await makeAssignment(teacher, 'COH-DATA', foreignTitle, 3)
  const deliveries = `/enrollments/${enrollment.enrollment_id}/submissions`
  const ownDelivery = async () => (await request(deliveries, 200, { token: learner })).items
    .find(item => item.assignment_id === assignment.id)

  const page = await newBrowser()
  await page.goto(web.href)
  await page.login('coder-01@example.test')
  requireCheck('Coder opens server-backed deliveries', await page.nav('Entregas') && await page.waitText('Mis entregas'))
  requireCheck('Pending activity shows no submission yet', await waitFor(page,
    `(${card})?.textContent.includes('Pendiente') && (${card})?.textContent.includes('Aún no hay un envío registrado')`))
  const pendingText = await page.text()
  requireCheck('Overdue activity is shown and unpublished or other-cohort activities stay hidden',
    pendingText.includes(overdueTitle) && pendingText.includes('Vencida') && !pendingText.includes(draftTitle) &&
    !pendingText.includes(foreignTitle) && !pendingText.includes('datos locales de demostración'))
  requireCheck('Reviewed filter excludes the pending activity', await page.set('#delivery-filter', 'reviewed') &&
    await waitFor(page, `!(${card})`))
  requireCheck('Show pending activities again', await page.set('#delivery-filter', 'all') &&
    await waitFor(page, `!!(${card})`))
  requireCheck('Open an editor scoped to the chosen activity', await page.click('Registrar entrega', `(${card})`))
  requireCheck('Unsafe portfolio format stays in the editor', await setPortfolio(page, 'http://example.test/artifact') &&
    await page.click('Guardar entrega', `(${card})`) && await page.waitText('Introduce un enlace HTTPS válido'))
  requireCheck('The invalid link had no persistence side effect', (await ownDelivery()).submission === null)

  const url = 'https://example.test/synthetic-artifact'
  requireCheck('Save the first HTTPS portfolio link', await setPortfolio(page, url) &&
    await page.click('Guardar entrega', `(${card})`) && await page.waitText('Envío guardado.'))
  const first = (await ownDelivery()).submission
  requireCheck('Portfolio link and first revision are persisted', first?.revision === 1 && first.portfolio_url === url &&
    await page.ev(`(${card})?.querySelector('a')?.getAttribute('rel') === 'noopener noreferrer'`))
  requireCheck('Resubmit with the optional link removed', await page.click('Editar enlace y reenviar', `(${card})`) &&
    await setPortfolio(page, '') && await page.click('Guardar reentrega', `(${card})`) && await page.waitText('Envío guardado.'))
  const second = (await ownDelivery()).submission
  requireCheck('Resubmission preserves the ID and first submission time', second?.id === first.id &&
    second.first_submitted_at === first.first_submitted_at && second.revision === 2 && second.portfolio_url === null)

  await request(`/submissions/${second.id}/review`, 200, {
    method: 'POST', token: teacher, body: { expected_revision: second.revision },
  })
  requireCheck('Reload the learner view after the teacher review', await page.nav('Inicio') && await page.nav('Entregas'))
  requireCheck('Reviewed delivery is visible and closed to edits', await waitFor(page,
    `(${card})?.textContent.includes('Revisada') && !(${card})?.querySelector('button')`))

  await request(deliveries, 403, { token: reader })
  requireCheck('API rejects the unauthorized reader', true)
  requireCheck('Browser reports no uncaught exceptions', errors.length === 0)
} catch {
  check('Learner delivery browser journey completed', false)
} finally {
  finish()
}
