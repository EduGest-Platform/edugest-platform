/** KAN-174: record an absence and book a second individual interview from the dossier. */
import { readFileSync } from 'node:fs'
import { check, errors, finish, newBrowser, sleep } from './cdp.mjs'

const web = new URL(process.env.WEB_URL ?? 'http://localhost:8443/')
const api = new URL(process.env.GISTAR_API ?? 'http://localhost:8000')
for (const url of [web, api]) {
  if (url.protocol !== 'http:' || !['localhost', '127.0.0.1'].includes(url.hostname) ||
      url.username || url.password || url.pathname !== '/' || url.search || url.hash) {
    throw new Error('Local synthetic HTTP origins required')
  }
}
if (!process.env.GISTAR_DEMO_PASSWORD || !process.argv[2]) {
  throw new Error('Set the synthetic demo password and pass the interview fixture file')
}

const fixture = JSON.parse(readFileSync(process.argv[2], 'utf8'))
const panel = 'document.querySelector(\'section[aria-label="Citaciones de selección"]\')'
const path = '/api/v1/applications/' + fixture.id
const selector = 'seleccion.ia@gistar.example'

function requireCheck(label, result) {
  check(label, Boolean(result))
  if (!result) throw new Error(label)
}

async function waitFor(page, expression) {
  for (let i = 0; i < 50; i++) {
    if (await page.ev(expression)) return true
    await sleep(200)
  }
  return false
}

async function openDossier(page) {
  await page.goto(web.href)
  requireCheck('The sign-in form is ready', await page.waitText('Iniciar sesión'))
  await page.login(selector)
  requireCheck('Selection opens the application inbox', await page.waitText('Candidaturas') && await page.nav('Candidaturas'))
  requireCheck('Find the dedicated synthetic dossier', await page.waitText('Expedientes') &&
    await page.set('#application-search', fixture.code) &&
    await waitFor(page, `document.querySelector('main tbody')?.textContent.includes(${JSON.stringify(fixture.code)})`))
  requireCheck('Open the fixture interview panel', await page.ev(`(() => {
    const row = [...document.querySelectorAll('main tbody tr')].find(row => row.textContent.includes(${JSON.stringify(fixture.code)}))
    row?.querySelector('button')?.click()
    return !!row
  })()`) && await waitFor(page, `!!${panel}`))
}

try {
  const page = await newBrowser()
  await openDossier(page)
  requireCheck('The past individual interview is available for a result',
    await page.waitText('Entrevista individual · Programada') && await page.click('Registrar resultado', panel))
  requireCheck('An absence hides assessment fields and is saved',
    await page.set('#selection-appointment-outcome', 'no_show') &&
    await page.ev("!document.querySelector('#selection-appointment-assessment')") &&
    await page.click('Guardar resultado', panel) && await page.waitText('Ausencia registrada'))
  requireCheck('The second opportunity is an individual interview',
    await page.click('Agendar segunda oportunidad', panel) && await page.waitText('Nueva fecha para la cita') &&
    await page.ev(`${panel}.querySelector('fieldset').textContent.includes('Entrevista individual') &&
      !document.querySelector('#selection-appointment-kind')`))

  const date = new Date(Date.now() + 48 * 3600 * 1000)
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60000).toISOString().slice(0, 16)
  requireCheck('Booking the second interview retains the previous appointment',
    await page.set('#selection-appointment-time', local) &&
    await page.click('Guardar cita', panel) && await page.waitText('Cita anterior:'))

  const another = await newBrowser()
  await openDossier(another)
  requireCheck('The second browser sees both persisted interview records',
    await another.waitText('Ausencia registrada') && await another.waitText('Entrevista individual · Programada'))
  requireCheck('Selection retains its human decision boundary', await another.ev(`(async () => {
    const token = sessionStorage.getItem('gistar-api-token')
    const headers = { Authorization: 'Bearer ' + token }
    const base = ${JSON.stringify(new URL(path, api).href)}
    const [dossier, appointments] = await Promise.all([
      fetch(base, { headers }), fetch(base + '/selection-appointments', { headers }),
    ])
    if (!dossier.ok || !appointments.ok) return false
    const { items } = await appointments.json()
    const missed = items.find(item => item.state === 'no_show')
    const booked = items.find(item => item.state === 'scheduled')
    return (await dossier.json()).stage === 'convocada' && items.length === 2 &&
      items.every(item => item.kind === 'individual_interview') && !!missed && booked?.previous_id === missed.id
  })()`))
  requireCheck('No uncaught browser errors', errors.length === 0)
} catch (error) {
  check('Individual interview browser journey', false, error.message)
} finally {
  finish()
}
