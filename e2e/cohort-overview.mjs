/** KAN-201: server cohort analytics against the disposable academic seed. */
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

function requireCheck(name, ok) {
  check(name, Boolean(ok))
  if (!ok) throw new Error('Cohort analytics assertion failed')
}

async function waitFor(page, expression) {
  for (let attempt = 0; attempt < 50; attempt++) {
    if (await page.ev(expression)) return true
    await sleep(200)
  }
  return false
}

async function login(page, email) {
  requireCheck('The demo sign-in form is ready', await waitFor(page,
    "!!document.querySelector('#lg-email') && !!document.querySelector('#lg-pass')"))
  await page.login(email)
}

async function applyAttendancePeriod(page, from, to) {
  requireCheck('Attendance period controls are available',
    await page.set('#overview-attendance-from', from) && await page.set('#overview-attendance-to', to))
  requireCheck('Attendance period is submitted', await page.click('Aplicar periodo'))
}

const octoberIaTotals = `(() => {
  const section = [...document.querySelectorAll('main section')]
    .find(card => card.querySelector('h2')?.textContent === 'Asistencia')
  if (!section) return false
  const totals = new Map([...section.querySelectorAll('.tabular-nums')]
    .map(value => [value.previousElementSibling?.textContent, value.textContent]))
  return totals.get('Días asistidos') === '34'
    && totals.get('Días con ausencia justificada') === '3'
    && totals.get('Días con ausencia sin justificar') === '1,5'
    && totals.get('Días sin registrar') === '5,5'
})()`

const iaDeliveries = `(() => {
  const row = [...document.querySelectorAll('main tbody tr')]
    .find(item => item.cells[0]?.textContent === 'Proyecto integrador IA')
  if (!row || row.cells.length !== 7) return false
  const [onTime, late, pending, overdue, reviewed] = [...row.cells].slice(2).map(cell => Number(cell.textContent))
  return onTime === 9 && late === 1 && pending + overdue === 1 && reviewed === 8
})()`

const iaCompetencies = `(() => {
  const row = [...document.querySelectorAll('main h3')].find(item => item.textContent === 'C1 · Python')
  return row?.parentElement.querySelector('[role="img"]')?.getAttribute('aria-label')
    === 'Nivel 1: 4 de 11, Nivel 2: 3 de 11, Nivel 3: 3 de 11, Sin evaluar: 1 de 11'
})()`

try {
  const teacher = await newBrowser()
  await teacher.goto(web.href)
  await login(teacher, 'docente@gistar.example')
  requireCheck('Teacher navigation is ready', await waitFor(teacher,
    `document.querySelector('nav[aria-label="Navegación principal"]')?.textContent.includes('Analítica del grupo')`))
  requireCheck('Teacher can open server group analytics', await teacher.nav('Analítica del grupo'))
  requireCheck('Seed IA cohort is loaded', await waitFor(teacher, "document.querySelector('#overview-cohort')?.value === 'COH-IA'"))

  await applyAttendancePeriod(teacher, '2026-10-01', '2026-10-31')
  requireCheck('October attendance matches the seeded half-day totals', await waitFor(teacher, octoberIaTotals))
  requireCheck('Published assignment counts match the fixture', await waitFor(teacher, iaDeliveries))
  requireCheck('Current competency levels match the fixture', await waitFor(teacher, iaCompetencies))

  await applyAttendancePeriod(teacher, '2026-10-31', '2026-10-01')
  requireCheck('Reversed attendance dates are rejected before changing totals',
    await teacher.waitText('La fecha de inicio debe ser anterior o igual a la fecha final.') && await teacher.ev(octoberIaTotals))

  await applyAttendancePeriod(teacher, '2025-01-01', '2025-01-02')
  requireCheck('Empty attendance period is shown as missing data',
    await teacher.waitText('No hay registros de asistencia en este periodo.'))
  requireCheck('Attendance dates leave published deliveries and current competencies visible',
    await teacher.ev(iaDeliveries) && await teacher.ev(iaCompetencies))

  requireCheck('Teacher can switch to the Data cohort', await teacher.set('#overview-cohort', 'COH-DATA'))
  requireCheck('Switching cohorts replaces the previous result',
    await teacher.waitText('Dashboard y automatización') && await teacher.waitText('C1 · Fundamentos de datos')
    && !(await teacher.ev(iaDeliveries)))

  const recruiter = await newBrowser()
  await recruiter.goto(web.href)
  await login(recruiter, 'captacion.ia@gistar.example')
  requireCheck('Recruitment navigation has no group analytics entry', await waitFor(recruiter, `(() => {
    const menu = document.querySelector('nav[aria-label="Navegación principal"]')
    return !!menu && menu.textContent.includes('Candidaturas') && !menu.textContent.includes('Analítica del grupo')
  })()`))
  const endpoint = JSON.stringify(new URL('/api/v1/cohorts/COH-IA/progress-overview', api).href)
  requireCheck('API denies recruitment access to academic aggregates', await recruiter.ev(`(async () => {
    const token = sessionStorage.getItem('gistar-api-token')
    if (!token) return false
    const response = await fetch(${endpoint}, { headers: { Authorization: 'Bearer ' + token } })
    return response.status === 403
  })()`))
  requireCheck('No uncaught browser exceptions', errors.length === 0)
} catch {
  check('Cohort analytics browser journey completed', false)
} finally {
  finish()
}
