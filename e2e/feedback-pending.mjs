/** Teacher workflow on an isolated academic seed. */
import { check, errors, finish, newBrowser } from './cdp.mjs'
import { interceptWrites, tryDismiss, waitForWrite } from './pending-response.mjs'

const web = new URL(process.env.WEB_URL ?? 'http://localhost:8443/')
if (web.protocol !== 'http:' || !['localhost', '127.0.0.1'].includes(web.hostname)
    || web.username || web.password || !process.env.GISTAR_DEMO_PASSWORD) throw new Error('Use local synthetic services')

function requireCheck(label, ok) {
  check(label, Boolean(ok))
  if (!ok) throw new Error(label)
}

const page = await newBrowser()
await interceptWrites(page, '/(?:submissions/[^/]+/feedback-drafts|feedback-drafts/[^/]+(?:/approve)?)$')
const dialog = "document.querySelector('[role=dialog]')"

try {
  await page.goto(web.href)
  requireCheck('The teacher can sign in', await page.waitText('Iniciar sesión'))
  await page.login('docente@gistar.example')
  requireCheck('The delivery review can be opened', await page.nav('Entregas') &&
    await page.waitText('Revisar feedback') && await page.click('Revisar feedback') &&
    await page.waitText('Generar borrador'))
  requireCheck('Draft generation stays open after the server commits',
    await page.click('Generar borrador', dialog) && await waitForWrite(page, 0) && await tryDismiss(page, '#feedback-cohort'))
  await page.ev('window.delayedWrites[0].release()')
  requireCheck('The generated draft appears once', await page.waitText('Versión 1 · Borrador'))
  requireCheck('The teacher edits the original draft', await page.click('Editar borrador', dialog) &&
    await page.set('#feedback-edit-body', 'Nota sintética del docente.') &&
    await page.click('Guardar versión', dialog))
  requireCheck('Editing stays open after the server commits', await waitForWrite(page, 1) &&
    await tryDismiss(page, '#feedback-cohort'))
  await page.ev('window.delayedWrites[1].release()')
  requireCheck('The edited draft appears once', await page.waitText('Versión 2 · Borrador'))

  await page.ev("document.querySelector('[role=dialog] input[type=checkbox]').click(); window.dropNextWrite = true")
  requireCheck('Publishing stays open after the server commits',
    await page.click('Aprobar y publicar', dialog) && await waitForWrite(page, 2) && await tryDismiss(page, '#feedback-cohort'))
  await page.ev('window.delayedWrites[2].release()')
  requireCheck('Connection loss blocks another write until versions are read',
    await page.waitText('No se pudo confirmar el cambio') &&
    await page.ev(`Array.from(${dialog}.querySelectorAll('button')).find(button =>
      button.textContent === 'Aprobar y publicar')?.disabled`))
  requireCheck('The authoritative refresh shows the committed version',
    await page.click('Actualizar versiones', dialog) && await page.waitText('Versión 2 · Publicada') &&
    await page.ev('window.delayedWrites.length === 3'))
  await page.ev(`${dialog}.querySelector('[aria-label="Cerrar"]').click()`)
  requireCheck('Reopening displays the same published version', await page.click('Revisar feedback') &&
    await page.waitText('Versión 2 · Publicada'))
  requireCheck('No uncaught browser errors', errors.length === 0)
} catch (error) {
  check('Feedback write recovery', false, error.message)
} finally {
  finish()
}
