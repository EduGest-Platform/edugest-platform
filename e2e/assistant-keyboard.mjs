/** KAN-169: real keyboard submission keeps the chat editor ready for the next question. */
const web = new URL(process.env.WEB_URL ?? 'http://127.0.0.1:8443/')
for (const origin of [web, new URL(process.env.GISTAR_API ?? 'http://127.0.0.1:8000')]) {
  if (origin.protocol !== 'http:' || !['127.0.0.1', 'localhost'].includes(origin.hostname) ||
      origin.username || origin.password || origin.pathname !== '/' || origin.search || origin.hash) {
    throw new Error('Local synthetic HTTP origins required')
  }
}
if (!process.env.GISTAR_DEMO_PASSWORD) throw new Error('Set the synthetic demo password')

const { newBrowser, check, errors, finish, sleep } = await import('./cdp.mjs')

function requireCheck(name, ok) {
  check(name, Boolean(ok))
  if (!ok) throw new Error(name)
}

try {
  const page = await newBrowser()
  await page.goto(web.href)
  await page.login('docente@gistar.example')
  requireCheck('Teacher opens the API assistant', await page.nav('Asistente'))
  requireCheck('Keyboard can start from the editor', await page.set('#assistant-question', 'Si entrego el Recetario un día tarde, ¿me lo aceptan?'))
  await page.ev("document.querySelector('#assistant-question').focus()")
  await page.tab()
  requireCheck('Tab focuses Send', await page.ev(
    "document.activeElement?.matches('button[type=submit]:focus-visible') && document.activeElement.textContent.trim() === 'Enviar'"))
  await page.enter()
  requireCheck('Keyboard submission receives the final server citation', await page.waitText('Referencia: A1'))
  requireCheck('Focus stays in the editable question field after the response', await page.ev(
    "document.activeElement?.id === 'assistant-question' && !document.activeElement.readOnly && document.activeElement.value === ''"))

  await page.blockUrls(['*/api/v1/assistant/ask/stream'])
  await page.set('#assistant-question', '¿Qué dice la guía sobre el Recetario?')
  await page.tab()
  await page.enter()
  requireCheck('A connection failure is announced', await page.waitText('No se pudo consultar el asistente.'))
  requireCheck('Focus and the unsent draft stay available for retry', await page.ev(
    "document.activeElement?.id === 'assistant-question' && !document.activeElement.readOnly && document.activeElement.value.includes('Recetario')"))
  await page.blockUrls([])
  await page.networkLatency(1400)
  await page.tab()
  await page.enter()
  requireCheck('Stop is available while a real stream request is pending', await page.click('Detener consulta'))
  await sleep(1600)
  requireCheck('Stopping keeps the editor and ignores late responses', await page.ev(`(() => {
    const editor = document.querySelector('#assistant-question');
    return document.activeElement === editor && !editor.readOnly && editor.value.includes('Recetario')
      && document.querySelectorAll('.assistant-transcript article').length === 1
      && !document.querySelector('main [role=alert]');
  })()`))
  await page.networkLatency(0)
  requireCheck('No uncaught browser exceptions', errors.length === 0)
} catch (error) {
  check('Assistant keyboard journey', false, error.message)
} finally {
  finish()
}
