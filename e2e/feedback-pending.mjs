/** Teacher workflow on an isolated academic seed. */
import { check, errors, finish, newBrowser } from './cdp.mjs'
import { interceptWrites, tryDismiss, waitForWrite } from './pending-response.mjs'

const web = new URL(process.env.WEB_URL ?? 'http://localhost:8443/')
const api = new URL(process.env.GISTAR_API ?? 'http://localhost:8000')
if (![web, api].every(url => url.protocol === 'http:' && ['localhost', '127.0.0.1'].includes(url.hostname)
    && !url.username && !url.password && url.pathname === '/' && !url.search && !url.hash)
    || !process.env.GISTAR_DEMO_PASSWORD) throw new Error('Use local synthetic services')

function requireCheck(label, ok) {
  check(label, Boolean(ok))
  if (!ok) throw new Error(label)
}

const page = await newBrowser()
await interceptWrites(page, '/(?:submissions/[^/]+/feedback-drafts|feedback-drafts/[^/]+(?:/approve)?)$')
const dialog = "document.querySelector('[role=dialog]')"
const title = 'Entrega sintética para recuperar feedback ' + crypto.randomUUID().slice(0, 8)
const submissionRow = `Array.from(document.querySelectorAll('main li')).find(row => row.textContent.includes(${JSON.stringify(title)}))`

async function prepareSubmission() {
  return page.ev(`(async () => {
    const base = ${JSON.stringify(api.origin + '/api/v1')}
    const headers = { Authorization: 'Bearer ' + sessionStorage.getItem('gistar-api-token'), 'Content-Type': 'application/json' }
    const roster = await fetch(base + '/cohorts/COH-IA/attendance-summary', { headers })
    if (!roster.ok) return false
    const enrollment = (await roster.json()).items[0]?.enrollment_id
    if (!enrollment) return false
    const assignment = await fetch(base + '/cohorts/COH-IA/assignments', {
      method: 'POST', headers, body: JSON.stringify({
        title: ${JSON.stringify(title)}, due_at: new Date(Date.now() + 86400000).toISOString(),
        rubric: ['Criterio sintético de feedback'],
      }),
    })
    if (!assignment.ok) return false
    const id = (await assignment.json()).id
    const submission = await fetch(base + '/assignments/' + id + '/submissions/' + enrollment, {
      method: 'PUT', headers, body: JSON.stringify({
        portfolio_url: 'https://example.test/portfolio', check_results: { passed: 2, total: 3 },
      }),
    })
    return submission.ok
  })()`)
}

try {
  await page.goto(web.href)
  requireCheck('The teacher can sign in', await page.waitText('Iniciar sesión'))
  await page.login('docente@gistar.example')
  requireCheck('The teacher can prepare a synthetic submission with test results',
    await page.waitText('Entregas') && await prepareSubmission())
  requireCheck('The delivery review can be opened', await page.nav('Entregas') &&
    await page.waitText('Entregas para revisar') && await page.set('#feedback-cohort', 'COH-IA') &&
    await page.waitText(title) && await page.click('Revisar feedback', `(${submissionRow})`) &&
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
  requireCheck('Reopening displays the same published version', await page.click('Revisar feedback', `(${submissionRow})`) &&
    await page.waitText('Versión 2 · Publicada'))
  requireCheck('No uncaught browser errors', errors.length === 0)
} catch (error) {
  check('Feedback write recovery', false, error.message)
} finally {
  finish()
}
