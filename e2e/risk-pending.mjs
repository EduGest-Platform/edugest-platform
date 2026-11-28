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
const dialog = "document.querySelector('[role=dialog]')"
const note = 'Nota de apoyo sintética con respuesta perdida.'

try {
  await page.goto(web.href)
  requireCheck('The teacher can sign in', await page.waitText('Iniciar sesión'))
  await page.login('docente@gistar.example')
  requireCheck('The teacher can open alerts', await page.nav('alertas') && await page.waitText('Alertas de apoyo'))
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
  requireCheck('No uncaught browser errors', errors.length === 0)
} catch (error) {
  check('Risk intervention recovery', false, error.message)
} finally {
  finish()
}
