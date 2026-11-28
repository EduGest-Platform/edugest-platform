/** KAN-227: public catalogue -> selected offer -> existing registration; local synthetic services only. */
import { expectedApplicationOutcome, matchesApplicationOutcome } from './public-catalog-outcome.mjs'

const web = process.env.WEB_URL ?? 'http://localhost:8443/'
const api = process.env.GISTAR_API ?? 'http://localhost:8000'
for (const value of [web, api]) {
  if (!['localhost', '127.0.0.1'].includes(new URL(value).hostname)) throw new Error('Local synthetic services required')
}
const fixture = process.env.E2E_FIXTURE_ID ?? 'local-public-catalog'
if (!/^[a-zA-Z0-9-]{1,64}$/.test(fixture)) throw new Error('Invalid synthetic fixture identifier')
const expected = expectedApplicationOutcome(process.env.E2E_EXPECT_OUTCOME)
const callId = process.env.E2E_CALL_ID
if (!callId || !/^[a-zA-Z0-9_-]{1,30}$/.test(callId)) throw new Error('Set E2E_CALL_ID to the same synthetic call for both executions')
const { newBrowser, check, errors, finish, sleep } = await import('./cdp.mjs')
function requireCheck(name, ok) {
  check(name, Boolean(ok))
  if (!ok) throw new Error(name)
}
async function waitFor(page, expression) {
  for (let i = 0; i < 50; i++) {
    if (await page.ev(expression)) return true
    await sleep(200)
  }
  return false
}

try {
  const response = await fetch(`${api}/api/v1/public/courses?admission_state=abierta&limit=20`)
  if (!response.ok) throw new Error('Synthetic public catalogue unavailable')
  const { items } = await response.json()
  const offer = items.find((item) => item.id === callId)
  if (!offer) throw new Error('Configured synthetic call must be an open published offer')
  const closedResponse = await fetch(`${api}/api/v1/public/courses?admission_state=cerrada&limit=20`)
  if (!closedResponse.ok) throw new Error('Closed-offer fixture unavailable')
  const closedOffer = (await closedResponse.json()).items[0]
  if (!closedOffer) throw new Error('Seed must include a closed published offer')
  const page = await newBrowser()
  await page.goto(web)
  requireCheck('API login entry remains available', await page.waitText('Iniciar sesión'))
  requireCheck('Public welcome introduces the catalogue', await page.waitText('Encuentra tu próxima formación'))
  for (const label of ['ES', 'EN', 'Modo noche']) {
    await page.tab()
    requireCheck(`Keyboard reaches the ${label} appearance control`, await page.ev(`(() => {
      const control = document.activeElement;
      return control?.closest('[aria-label="Preferencias de apariencia"]')
        && control.textContent.trim() === ${JSON.stringify(label)} && control.matches(':focus-visible')
    })()`))
  }
  await page.tab()
  requireCheck('Keyboard reaches the catalogue action with a visible focus outline', await page.ev(`(() => {
    const action = document.activeElement;
    return action?.textContent.trim() === 'Explorar el catálogo'
      && action.matches(':focus-visible') && getComputedStyle(action).outlineStyle !== 'none'
  })()`))
  await page.blockUrls(['*/api/v1/public/courses*'])
  requireCheck('Public catalogue entry is available without login', await page.click('Explorar el catálogo'))
  requireCheck('Public navigation identifies the active view', await page.ev(`document.querySelector('nav[aria-label="Acceso público"] [aria-current="page"]')?.textContent.trim() === 'Ver formaciones'`))
  requireCheck('Connectivity failure offers a retry', await page.waitText('Volver a cargar formaciones'))
  await page.blockUrls([])
  await page.click('Volver a cargar formaciones')
  requireCheck('Published offers load after retry', await page.waitText('ofertas publicadas con este filtro'))
  await page.set('#public-admission-filter', 'cerrada')
  requireCheck('Closed published offer remains readable', await page.waitText(closedOffer.name))
  await page.ev(`(() => {
    const button = [...document.querySelectorAll('button')].find(item => item.getAttribute('aria-label') === ${JSON.stringify(`Ver formación: ${closedOffer.name}`)})
    button?.click()
  })()`)
  requireCheck('Closed detail has loaded', await page.waitText('Plazas ofertadas'))
  requireCheck('Closed offer has no apply action', await page.ev(`![...document.querySelectorAll('button')].some(item => item.textContent.trim() === 'Solicitar plaza')`))
  await page.click('Volver al catálogo')
  requireCheck('Returning preserves the admission filter and restores focus', await waitFor(page,
    `document.activeElement?.id === 'public-admission-filter' && document.activeElement.value === 'cerrada'`))
  await page.set('#public-admission-filter', 'abierta')
  requireCheck('Open published offer appears', await page.waitText(offer.name))
  await page.ev(`document.querySelector('#public-admission-filter').focus()`)
  await page.tab()
  requireCheck('Keyboard reaches an offer detail button', await page.ev(`document.activeElement?.matches('button[aria-label^="Ver formación"]:focus-visible')`))
  requireCheck('Open the expected offer', await page.ev(`(() => {
    const button = [...document.querySelectorAll('button')].find(item => item.getAttribute('aria-label') === ${JSON.stringify(`Ver formación: ${offer.name}`)})
    button?.click(); return !!button
  })()`))
  requireCheck('Offer detail loads from the server', await page.waitText('Plazas ofertadas'))
  requireCheck('Detail heading receives focus', await page.ev(`document.activeElement?.id === 'public-course-title'`))
  requireCheck('Human application CTA is available', await page.click('Solicitar plaza'))
  requireCheck('Chosen call stays pinned', await waitFor(page, `document.querySelector('#ins-call')?.value === ${JSON.stringify(offer.id)} && document.querySelector('#ins-call')?.disabled`))
  requireCheck('Application name receives focus', await page.ev(`document.activeElement?.id === 'ins-name'`))
  const selectedApplication = await page.ev('location.href')
  await page.ev('history.back()')
  requireCheck('Browser Back returns to the catalogue', await page.waitText('Formaciones disponibles'))
  await page.ev('history.forward()')
  requireCheck('Browser Forward restores the same pinned call', await waitFor(page,
    `document.querySelector('#ins-call')?.value === ${JSON.stringify(offer.id)} && document.querySelector('#ins-call')?.disabled`))
  await page.goto(selectedApplication)
  requireCheck('Reload keeps the selected call pinned', await waitFor(page,
    `document.querySelector('#ins-call')?.value === ${JSON.stringify(offer.id)} && document.querySelector('#ins-call')?.disabled`))
  await page.set('#ins-name', 'Persona Catálogo Sintética')
  await page.set('#ins-email', `catalog.${fixture.toLowerCase()}@example.test`)
  await page.set('#ins-mot', 'Solicitud sintética desde la ficha de formación publicada para verificar el recorrido.')
  await page.ev(`document.querySelector('form input[type=checkbox]').click()`)
  requireCheck('Submit uses the existing registration form', await page.click('Enviar candidatura'))
  requireCheck('Server returns a registration result', await waitFor(page, `document.body.innerText.includes('Candidatura recibida') || document.body.innerText.includes('Ya existe una candidatura')`))
  requireCheck(expected === 'created' ? 'First execution requires a receipt' : 'Repeat execution requires duplicate rejection',
    matchesApplicationOutcome(expected, await page.text()))
  requireCheck('Focus moves to the application result', await waitFor(page,
    'document.activeElement?.hasAttribute("data-application-feedback")'))
  requireCheck('No uncaught browser exceptions', errors.length === 0)
} catch (error) {
  check('Public catalogue journey completes', false, error instanceof Error ? error.message : 'Unknown error')
} finally {
  finish()
}
