/** Verify recovery of a committed synthetic note after the response is lost. */
import { check, errors, finish, newBrowser, sleep } from './cdp.mjs'
import { interceptWrites, tryDismiss, waitForWrite } from './pending-response.mjs'

const web = new URL(process.env.WEB_URL ?? 'http://localhost:8443/')
if (web.protocol !== 'http:' || !['localhost', '127.0.0.1'].includes(web.hostname)
    || web.username || web.password || !process.env.GISTAR_DEMO_PASSWORD) throw new Error('Use local synthetic services')

function requireCheck(label, ok) {
  check(label, Boolean(ok))
  if (!ok) throw new Error(label)
}

const page = await newBrowser()
await interceptWrites(page, '/risk-alerts/[^/]+/interventions$')
await page.initScript(`(() => {
  const fetch = window.fetch.bind(window)
  window.fetch = async (input, init) => {
    const path = new URL(input.url ?? input, location.href).pathname
    const method = init?.method ?? input.method ?? 'GET'
    if (method === 'GET' && path.endsWith('/COH-DATA/risk-alerts') && !window.releaseAlertList) {
      await new Promise(resolve => { window.releaseAlertList = resolve })
    }
    return fetch(input, init)
  }
})()`)
const dialog = "document.querySelector('[role=dialog]')"
const note = 'Nota de apoyo sintética con respuesta perdida.'
const closureNote = 'Cierre docente sintético tras revisar el historial.'

try {
  await page.goto(web.href)
  requireCheck('The teacher can sign in', await page.waitText('Iniciar sesión'))
  await page.login('docente@gistar.example')
  requireCheck('The teacher can open aggregate analytics and pick a cohort',
    await page.nav('Analítica del grupo') && await page.waitText('Revisar alertas de esta cohorte') &&
    await page.set('#overview-cohort', 'COH-DATA'))
  requireCheck('The alert view opens with the same authorised cohort',
    await page.click('Revisar alertas de esta cohorte') && await page.waitText('Alertas de apoyo') &&
    await page.waitText('Cargando alertas…') &&
    await page.ev("document.querySelector('#risk-cohort').value === 'COH-DATA'"))
  requireCheck('The list announces loading with decoration hidden from assistive technology',
    await page.ev(`[...document.querySelectorAll('[role=status]')].some(status =>
      status.textContent.includes('Cargando alertas…') && status.querySelector('[aria-hidden=true]'))`))
  let responseHeld = false
  for (let attempt = 0; attempt < 30 && !responseHeld; attempt++) {
    responseHeld = await page.ev("typeof window.releaseAlertList === 'function'")
    if (!responseHeld) await sleep(100)
  }
  requireCheck('The loading state was verified while the response was held', responseHeld)
  await page.ev('window.releaseAlertList()')
  requireCheck('The loading indicator gives way to the empty state',
    await page.waitText('No hay alertas sintéticas con este filtro.') &&
    await page.ev("!document.body.innerText.includes('Cargando alertas…')"))
  const cohortSelector = '#risk-cohort'
  let fixtureCohortAvailable = false
  for (let attempt = 0; attempt < 40 && !fixtureCohortAvailable; attempt++) {
    fixtureCohortAvailable = await page.ev(`!!document.querySelector('${cohortSelector} option[value="COH-IA"]')`)
    if (!fixtureCohortAvailable) await sleep(150)
  }
  requireCheck('Select the cohort containing the synthetic risk fixture',
    fixtureCohortAvailable && await page.set(cohortSelector, 'COH-IA'))
  requireCheck('The teacher can review the synthetic alert', await page.waitText('Revisar alerta') &&
    await page.click('Revisar alerta') && await page.waitText('Registrar intervención'))
  await page.ev('window.dropNextWrite = true')
  requireCheck('Commit the support note while its response is pending',
    await page.set('#risk-kind', 'support') && await page.set('#risk-note', note) &&
    await page.click('Registrar intervención', dialog) && await waitForWrite(page, 0))
  requireCheck('All dismissal paths and the cohort selector remain blocked',
    await tryDismiss(page, '#risk-cohort'))
  await page.ev('window.delayedWrites[0].release()')
  requireCheck('The refreshed history shows the committed note without enabling retry',
    await page.waitText('Cerrar comprobación sin reenviar') && await page.ev(`(() => {
      const dialog = ${dialog}
      return dialog.querySelector('#risk-note').value === ${JSON.stringify(note)} &&
        Array.from(dialog.querySelectorAll('li')).filter(item => item.textContent.includes(${JSON.stringify(note)})).length === 1 &&
        dialog.querySelector('button[type=submit]').disabled &&
        !Array.from(dialog.querySelectorAll('button')).some(button =>
          button.textContent.includes('He comprobado que la intervención no se registró'))
    })()`))
  await page.click('Cerrar comprobación sin reenviar', dialog)
  await page.ev(`${dialog}.querySelector('[aria-label="Cerrar"]').click()`)
  requireCheck('Reopening shows one single intervention and nothing was resent', await page.waitText('Revisar alerta') &&
    await page.click('Revisar alerta') &&
    await page.waitText(note) && await page.ev(`window.delayedWrites.length === 1 &&
      Array.from(${dialog}.querySelectorAll('li')).filter(item => item.textContent.includes(${JSON.stringify(note)})).length === 1`))
  requireCheck('Closure requires explicit confirmation before sending',
    await page.set('#risk-kind', 'closure') && await page.set('#risk-note', 'Borrador de cierre.') &&
    await page.ev(`${dialog}.querySelector('button[type=submit]').disabled && window.delayedWrites.length === 1`))
  await page.ev(`${dialog}.querySelector('input[type=checkbox]').click()`)
  requireCheck('Editing the closure note requires a new confirmation',
    await page.set('#risk-note', closureNote) &&
    await page.ev(`${dialog}.querySelector('button[type=submit]').disabled`))
  await page.ev(`${dialog}.querySelector('input[type=checkbox]').click()`)
  requireCheck('A confirmed closure is the second write',
    await page.click('Cerrar alerta', dialog) && await waitForWrite(page, 1))
  await page.ev('window.delayedWrites[1].release()')
  requireCheck('Closure renders the saved note and keeps the alert read-only',
    await page.waitText('Alerta cerrada.') && await page.waitText(closureNote) &&
    await page.ev(`!${dialog}.querySelector('button[type=submit]')`))
  await page.ev(`${dialog}.querySelector('[aria-label="Cerrar"]').click()`)
  requireCheck('The closed filter finds the alert and reopening retains the closure',
    await page.set('#risk-state', 'closed') && await page.waitText('Revisar alerta') &&
    await page.click('Revisar alerta') && await page.waitText(closureNote) &&
    await page.ev(`!${dialog}.querySelector('button[type=submit]') && window.delayedWrites.length === 2`))
  requireCheck('No uncaught browser errors', errors.length === 0)
} catch (error) {
  check('Risk intervention recovery', false, error.message)
} finally {
  finish()
}
