/** Teacher publication and learner visibility on an isolated academic seed. */
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
const feedbackNote = 'Nota sintética del docente.'
const learnerCard = `Array.from(document.querySelectorAll('main section')).find(card =>
  card.querySelector('h2')?.textContent === ${JSON.stringify(title)})`

async function prepareSubmission(enrollmentId) {
  return page.ev(`(async () => {
    const base = ${JSON.stringify(api.origin + '/api/v1')}
    const headers = { Authorization: 'Bearer ' + sessionStorage.getItem('gistar-api-token'), 'Content-Type': 'application/json' }
    const enrollment = ${JSON.stringify(enrollmentId)}
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
  const learner = await newBrowser()
  await learner.goto(web.href)
  await learner.login('coder-01@example.test')
  const enrollmentId = await learner.ev(`(async () => {
    const token = sessionStorage.getItem('gistar-api-token')
    const response = await fetch(${JSON.stringify(new URL('/api/v1/me/enrollments', api).href)}, {
      headers: { Authorization: 'Bearer ' + token },
    })
    if (!response.ok) return null
    return (await response.json()).items.find(item =>
      item.status === 'activa' && item.cohort_id === 'COH-IA')?.enrollment_id
  })()`)
  requireCheck('The synthetic learner has an active enrollment in the test cohort', enrollmentId)

  await page.goto(web.href)
  requireCheck('The teacher can sign in', await page.waitText('Iniciar sesión'))
  await page.login('docente@gistar.example')
  requireCheck('The teacher can prepare a synthetic submission with test results',
    await page.waitText('Entregas') && await prepareSubmission(enrollmentId))
  requireCheck('The delivery review can be opened', await page.nav('Entregas') &&
    await page.waitText('Entregas para revisar') && await page.set('#feedback-cohort', 'COH-IA') &&
    await page.waitText(title) && await page.click('Revisar feedback', `(${submissionRow})`) &&
    await page.waitText('Generar borrador'))
  requireCheck('Draft generation stays open after the server commits',
    await page.click('Generar borrador', dialog) && await waitForWrite(page, 0) && await tryDismiss(page, '#feedback-cohort'))
  await page.ev('window.delayedWrites[0].release()')
  requireCheck('The generated draft appears once', await page.waitText('Versión 1 · Borrador'))
  requireCheck('The teacher edits the original draft', await page.click('Editar borrador', dialog) &&
    await page.set('#feedback-edit-body', feedbackNote) &&
    await page.click('Guardar versión', dialog))
  requireCheck('Editing stays open after the server commits', await waitForWrite(page, 1) &&
    await tryDismiss(page, '#feedback-cohort'))
  await page.ev('window.delayedWrites[1].release()')
  requireCheck('The edited draft appears once', await page.waitText('Versión 2 · Borrador'))
  requireCheck('The learner can open feedback on their own submitted activity',
    await learner.nav('Entregas') && await learner.waitText(title) && await learner.ev(`(() => {
      const summary = (${learnerCard})?.querySelector('details summary')
      summary?.click()
      return !!summary
    })()`))
  requireCheck('The edited draft remains invisible to the learner before approval',
    await learner.waitText('Todavía no hay feedback publicado.') &&
    await learner.ev(`!(${learnerCard})?.textContent.includes(${JSON.stringify(feedbackNote)})`))


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
  requireCheck('After approval the learner sees the exact published version on refresh',
    await learner.click('Actualizar feedback', `(${learnerCard})`) && await learner.waitText(feedbackNote) &&
    await learner.ev(`(() => {
      const feedback = (${learnerCard})?.querySelector('details')
      return feedback?.textContent.includes('Versión 2') &&
        feedback.textContent.includes(${JSON.stringify(feedbackNote)})
    })()`))
  requireCheck('No uncaught browser errors', errors.length === 0)
} catch (error) {
  check('Feedback write recovery', false, error.message)
} finally {
  finish()
}
