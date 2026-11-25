/** KAN-49 / KAN-177: own learner progress against disposable synthetic services. */
const web = new URL(process.env.WEB_URL ?? 'http://localhost:8443/')
const api = new URL(process.env.GISTAR_API ?? 'http://localhost:8000')
for (const url of [web, api]) {
  if (url.protocol !== 'http:' || !['localhost', '127.0.0.1'].includes(url.hostname) ||
      url.username || url.password || url.pathname !== '/' || url.search || url.hash) {
    throw new Error('Local synthetic HTTP origins required')
  }
}
if (!process.env.GISTAR_DEMO_PASSWORD) throw new Error('Set the synthetic demo password')

const { newBrowser, check, errors, finish, sleep } = await import('./cdp.mjs')

function requireCheck(label, result) {
  check(label, Boolean(result))
  if (!result) throw new Error('Learner progress assertion failed')
}

async function waitFor(page, expression) {
  for (let attempt = 0; attempt < 50; attempt++) {
    const value = await page.ev(expression)
    if (value) return value
    await sleep(200)
  }
  return null
}

async function apiStatus(page, path) {
  const url = JSON.stringify(new URL(`/api/v1${path}`, api).href)
  return page.ev(`(async () => {
    const token = sessionStorage.getItem('gistar-api-token')
    if (!token) return null
    const response = await fetch(${url}, { headers: { Authorization: 'Bearer ' + token } })
    return response.status
  })()`)
}

async function openLearnerProgress(page) {
  const enrollmentId = await waitFor(page, "document.querySelector('#learner-enrollment')?.value")
  requireCheck('Own enrollment is listed', enrollmentId)
  requireCheck('Server attendance, competencies and deliveries are rendered', await waitFor(page, `(() => {
    const main = document.querySelector('main')
    if (!main) return false
    const headings = [...main.querySelectorAll('h2')].map(heading => heading.textContent)
    return headings.join('|') === 'Asistencia|Competencias|Entregas'
      && main.textContent.includes('Nivel ')
      && main.querySelectorAll('dl dd').length === 5
      && !![...main.querySelectorAll('section')].at(-1)?.querySelector('li')
      && !main.textContent.includes('datos locales de demostración')
  })()`))
  return enrollmentId
}

try {
  const learner = await newBrowser()
  const applicant = await newBrowser()
  await learner.goto(web.href)
  requireCheck('API login form is available', await learner.waitText('Iniciar sesión'))
  await learner.login('coder-01@example.test')
  requireCheck('Learner can navigate to own progress', await learner.nav('Mi progreso'))
  const enrollmentId = await openLearnerProgress(learner)

  await learner.goto(web.href)
  requireCheck('Session survives browser reload', await learner.nav('Mi progreso'))
  requireCheck('Same enrollment is shown after reload', await openLearnerProgress(learner) === enrollmentId)

  await applicant.goto(web.href)
  await applicant.login('aspirante-01@example.test')
  requireCheck('Aspirant menu has no learner progress view', await applicant.ev(`(() => {
    const menu = document.querySelector('nav[aria-label="Navegación principal"]')
    return !!menu && menu.textContent.includes('Mi candidatura') && !menu.textContent.includes('Mi progreso')
  })()`))
  for (const resource of ['attendance', 'competencies']) {
    requireCheck(`Aspirant cannot read the learner's ${resource}`,
      await apiStatus(applicant, `/me/enrollments/${encodeURIComponent(enrollmentId)}/${resource}`) === 404)
  }
  requireCheck('Learner and aspirant contexts stay independent',
    await apiStatus(learner, `/me/enrollments/${encodeURIComponent(enrollmentId)}/attendance`) === 200)
  requireCheck('No uncaught browser exceptions', errors.length === 0)
} catch {
  check('Learner progress browser journey completed', false)
} finally {
  finish()
}
