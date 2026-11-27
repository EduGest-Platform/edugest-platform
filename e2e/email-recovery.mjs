/** Use a disposable queue with no worker. No SMTP calls are made. */
import { check, errors, finish, newBrowser, sleep } from './cdp.mjs'

const web = new URL(process.env.WEB_URL ?? 'http://localhost:8443/')
const api = new URL(process.env.GISTAR_API ?? 'http://localhost:8000')
if (![web, api].every(url => url.protocol === 'http:' && ['localhost', '127.0.0.1'].includes(url.hostname)
    && !url.username && !url.password && url.pathname === '/' && !url.search && !url.hash)
    || !process.env.GISTAR_DEMO_PASSWORD) throw new Error('Use local synthetic services')

const page = await newBrowser()
await page.initScript(`(() => {
  const fetch = window.fetch.bind(window)
  window.emailWrites = []
  window.fetch = async (input, init) => {
    const path = new URL(input.url ?? input, location.href).pathname
    if ((init?.method ?? input.method) !== 'POST' || !path.endsWith('/email/notifications')) return fetch(input, init)
    const request = new Request(input, init)
    const payload = await request.clone().json()
    const response = await fetch(request)
    const body = await response.clone().json()
    const calls = window.emailWrites
    calls.push({ payload, message_id: body.message_id, status: response.status })
    if (!sessionStorage.getItem('test-email-dropped')) {
      await new Promise(release => { calls.at(-1).release = release })
      sessionStorage.setItem('test-email-dropped', JSON.stringify(calls[0]))
      throw new TypeError('Synthetic connection loss after queue commit')
    }
    return response
  }
})()`)

function requireCheck(label, ok) {
  check(label, Boolean(ok))
  if (!ok) throw new Error(label)
}

try {
  await page.goto(web.href)
  requireCheck('The teacher can sign in', await page.waitText('Iniciar sesión'))
  await page.login('docente@gistar.example')
  requireCheck('The teacher can inspect the synthetic queue', await page.nav('Cohortes') &&
    await page.waitText('Matrícula destinataria'))
  const historySelector = 'No hay solicitudes registradas.'
  requireCheck('The disposable cohort starts with an empty queue', await page.waitText(historySelector))
  let enrollment
  for (let attempt = 0; attempt < 40 && !enrollment; attempt++) {
    enrollment = await page.ev("document.querySelector('#email-recipient option:nth-child(2)')?.value")
    if (!enrollment) await sleep(100)
  }
  const cohort = await page.ev("document.querySelector('#academic-cohort').value")
  const other = await page.ev("Array.from(document.querySelector('#academic-cohort').options).find(option => !option.selected)?.value")
  const topic = 'Aviso sintético tras una respuesta perdida ' + crypto.randomUUID().slice(0, 8)
  requireCheck('The teacher confirms the exact payload', enrollment && other &&
    await page.set('#email-recipient', enrollment) && await page.set('#email-topic', topic) &&
    await page.click('Revisar aviso') && await page.click('Confirmar solicitud de envío'))
  for (let attempt = 0; attempt < 40; attempt++) {
    if (await page.ev('typeof window.emailWrites[0]?.release === "function"')) break
    await sleep(100)
  }
  requireCheck('The enqueue committed and cohort change is blocked while pending',
    await page.ev("window.emailWrites[0]?.status === 202 && document.querySelector('#academic-cohort').disabled"))
  await page.nav('Calendario')
  requireCheck('Menu navigation keeps the pending email in scope',
    await page.ev("!!document.querySelector('#academic-cohort')"))
  await page.ev('window.emailWrites[0].release()')
  requireCheck('A lost response shows the original request', await page.waitText('Reintentar con la misma referencia'))
  requireCheck('A cohort change and return restores the reference', await page.set('#academic-cohort', other) &&
    await page.waitText('Matrícula destinataria') && await page.set('#academic-cohort', cohort) &&
    await page.waitText('Reintentar con la misma referencia'))
  await page.goto(web.href)
  requireCheck('A full reload restores the exact request', await page.nav('Cohortes') && await page.waitText('Matrícula destinataria') &&
    await page.set('#academic-cohort', cohort) && await page.waitText(topic) &&
    await page.ev("document.body.innerText.includes(JSON.parse(sessionStorage.getItem('test-email-dropped')).payload.idempotency_key)"))
  requireCheck('The retry returns the original message', await page.click('Reintentar con la misma referencia') &&
    await page.waitText('Solicitud aceptada en la cola') && await page.ev(`(() => {
      const old = JSON.parse(sessionStorage.getItem('test-email-dropped'))
      const retry = window.emailWrites[0]
      return retry.status === 202 && retry.message_id === old.message_id &&
        JSON.stringify(retry.payload) === JSON.stringify(old.payload)
    })()`))
  const history = new URL(`/api/v1/cohorts/${cohort}/email/notifications`, api)
  requireCheck('Exactly one outbox row exists and no delivery was attempted', await page.ev(`(async () => {
    const token = sessionStorage.getItem('gistar-api-token')
    const response = await fetch(${JSON.stringify(history.href)}, { headers: { Authorization: 'Bearer ' + token } })
    const entries = await response.json()
    return response.ok && entries.length === 1 && entries[0].attempts === 0 &&
      entries[0].status === 'pending' && entries[0].message_id === window.emailWrites[0].message_id
  })()`))
  requireCheck('No uncaught browser errors', errors.length === 0)
} catch (error) {
  check('Recovering a synthetic email request', false, error.message)
} finally {
  finish()
}
