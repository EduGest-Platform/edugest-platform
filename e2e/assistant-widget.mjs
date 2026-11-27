/** Exercise the assistant widget against disposable sessions and intercepted SSE. */
import { check, errors, finish, newBrowser, sleep } from './cdp.mjs'

const web = new URL(process.env.WEB_URL ?? 'http://localhost:8443/')
if (web.protocol !== 'http:' || !['localhost', '127.0.0.1'].includes(web.hostname) ||
    web.username || web.password || web.pathname !== '/' || web.search || web.hash) {
  throw new Error('Local synthetic HTTP origin required')
}
if (!process.env.GISTAR_DEMO_PASSWORD) throw new Error('Set the synthetic demo password')

const B = await newBrowser()
await B.initScript(`(() => {
  const original = window.fetch.bind(window)
  window.assistantTestCalls = []
  window.fetch = async (request, options) => {
    const url = new URL(typeof request === 'string' ? request : request.url, location.href)
    const method = options?.method ?? request.method ?? 'GET'
    if (url.pathname !== '/api/v1/assistant/ask/stream' || method.toUpperCase() !== 'POST') return original(request, options)
    const status = window.assistantTestError ? 503 : 200
    const body = request instanceof Request ? await request.clone().json() : JSON.parse(options.body)
    await new Promise(release => window.assistantTestCalls.push({ question: body.question, cohort: body.cohort_id, status, release }))
    const data = status === 503 ? { detail: 'Synthetic unavailable' } : {
      status: 'no_source', mode: 'extractive', retrieval: 'keyword', answer: 'No consta',
      citations: [], as_of: '2026-11-26', scope_cohorts: ['COH-IA'], source_kind: 'documents', record: null,
    }
    if (status !== 200) return new Response(JSON.stringify(data), { status, headers: { 'Content-Type': 'application/json' } })
    const frame = (event, payload) => 'event: ' + event + '\\n' + 'data: ' + JSON.stringify(payload) + '\\n\\n'
    return new Response(frame('phase', { source_kind: 'documents' }) + frame('delta', { text: 'No consta' }) + frame('answer', data), { status, headers: { 'Content-Type': 'text/event-stream' } })
  }
})()`)

try {
  await B.goto(web.href)
  if (!await B.waitText('Iniciar sesión')) throw new Error('The sign-in screen did not load')
  await B.login('docente@gistar.example')
  if (!await B.waitText('Asistente')) throw new Error('The teacher widget did not load')
// KAN-268 · Floating assistant: deterministic browser responses, real keyboard events.
const editor = '[aria-label="Pregunta al asistente"]'
const launch = '[aria-label="Abrir asistente EduGest"]'

async function releaseAssistantCall(index, question, status, cohort = null) {
  for (let attempt = 0; attempt < 30; attempt++) {
    const recorded = await B.ev(`(() => {
      const calls = window.assistantTestCalls;
      const call = calls[${index}];
      if (calls.length !== ${index + 1} || call.question !== ${JSON.stringify(question)} || call.status !== ${status} || call.cohort !== ${JSON.stringify(cohort)}) return false;
      call.release();
      return true;
    })()`)
    if (recorded) return true
    await sleep(100)
  }
  return false
}
await B.ev(`document.querySelector('${launch}').click()`)
await B.set(editor, 'Pregunta sintética de prueba')
check('Contador accesible de caracteres', await B.ev(`document.querySelector('#assistant-question-length').textContent === document.querySelector('${editor}').value.length + '/500 caracteres' && document.querySelector('${editor}').getAttribute('aria-describedby') === 'assistant-question-length'`))
await B.enter()
check('Asistente conserva foco durante consulta por Enter', await B.ev(`document.activeElement.matches('${editor}') && document.activeElement.readOnly`))
check('Interceptor atendió primera consulta', await releaseAssistantCall(0, 'Pregunta sintética de prueba', 200))
check('Asistente muestra respuesta', await B.waitText('No consta en la documentación'))
check('Editor conserva foco y vuelve a ser editable', await B.ev(`document.activeElement.matches('${editor}') && !document.activeElement.readOnly`))
await B.set(editor, 'Segunda pregunta sintética')
await B.ev('window.assistantTestError = true')
await B.enter()
check('Interceptor atendió segunda consulta', await releaseAssistantCall(1, 'Segunda pregunta sintética', 503))
check('Asistente muestra error 503 esperado', await B.waitText('El servidor ha tenido un problema. Inténtalo de nuevo en unos minutos.'))
check('Mensaje exacto del error', await B.ev(`document.querySelector('dialog [role=alert]')?.textContent === 'El servidor ha tenido un problema. Inténtalo de nuevo en unos minutos.'`))
check('Editor editable y enfocado tras error', await B.ev(`document.activeElement.matches('${editor}') && !document.activeElement.readOnly`))
await B.set(editor, 'Tercera pregunta sintética')
await B.ev('window.assistantTestError = false')
await B.ev('document.querySelector("[aria-label=\\"Enviar pregunta\\"]").focus(); document.activeElement.click()')
check('Envío por botón devuelve foco al editor', await B.ev(`document.activeElement.matches('${editor}')`))
await B.ev('document.querySelector("[aria-label=\\"Cerrar asistente\\"]").focus()')
check('Interceptor atendió tercera consulta', await releaseAssistantCall(2, 'Tercera pregunta sintética', 200))
check('Tercera respuesta completada', await B.waitText('No consta en la documentación') && await B.ev(`new Promise(resolve => { const deadline = Date.now() + 6000; const poll = () => { if (!document.querySelector('${editor}').readOnly) resolve(true); else if (Date.now() > deadline) resolve(false); else setTimeout(poll, 50) }; poll() })`))
check('Respuesta no roba foco al usuario', await B.ev('document.activeElement.getAttribute("aria-label") === "Cerrar asistente"'))
await B.ev(`document.querySelector('${editor}').focus()`)
await B.set(editor, 'Consulta que será detenida')
await B.enter()
check('Consulta en curso antes de detener', await B.ev(`document.querySelector('${editor}').readOnly`))
await B.ev('document.querySelector("[aria-label=\\"Detener consulta\\"]").click()')
check('Detener restaura pregunta y edición', await B.ev(`document.querySelector('${editor}').value === 'Consulta que será detenida' && !document.querySelector('${editor}').readOnly`))
check('Interceptor libera consulta detenida', await releaseAssistantCall(3, 'Consulta que será detenida', 200))
await sleep(200)
check('Respuesta tardía no altera conversación', await B.ev(`!document.querySelector('dialog [role=log]').textContent.includes('Consulta que será detenida')`))
await B.set(editor, 'Consulta que será eliminada')
await B.enter()
check('Consulta en curso antes de limpiar', await B.ev(`document.querySelector('${editor}').readOnly`))
await B.ev(`Array.from(document.querySelectorAll('dialog button')).find(button => button.textContent === 'Limpiar conversación').click()`)
check('Limpiar devuelve foco al editor', await B.ev(`document.activeElement.matches('${editor}')`))
check('Limpiar elimina historial y borrador', await B.ev(`document.querySelector('${editor}').value === '' && !document.querySelector('${editor}').readOnly && !document.querySelector('dialog [role=log] article')`))
check('Interceptor libera consulta eliminada', await releaseAssistantCall(4, 'Consulta que será eliminada', 200))
await sleep(200)
check('Respuesta tardía no repuebla historial limpio', await B.ev(`!document.querySelector('dialog [role=log] article') && !document.querySelector('dialog [role=log]').textContent.includes('Consulta que será eliminada') && document.querySelector('${editor}').value === ''`))
await B.set(editor, 'Consulta después de limpiar')
await B.enter()
check('Interceptor acepta nueva consulta', await releaseAssistantCall(5, 'Consulta después de limpiar', 200))
check('Nueva conversación funciona', await B.waitText('No consta en la documentación') && await B.ev(`document.querySelectorAll('dialog [role=log] article').length === 1`))
await B.escape()
await sleep(200)
check('Escape cierra asistente y restaura foco', await B.ev(`!document.querySelector('dialog[open]') && document.activeElement.matches('${launch}')`))

await B.ev(`document.querySelector('${launch}').click()`)
await B.set(editor, 'Consulta durante cierre')
await B.enter()
check('Consulta activa antes de cerrar', await B.ev(`document.querySelector('${editor}').readOnly`))
await B.escape()
await sleep(200)
check('Escape durante consulta restaura foco', await B.ev(`!document.querySelector('dialog[open]') && document.activeElement.matches('${launch}')`))
check('Interceptor libera consulta cerrada', await releaseAssistantCall(6, 'Consulta durante cierre', 200))
await B.ev(`document.querySelector('${launch}').click()`)
await sleep(200)
check('Reapertura conserva borrador sin respuesta tardía', await B.ev(`document.querySelector('${editor}').value === 'Consulta durante cierre' && !document.querySelector('${editor}').readOnly && document.querySelectorAll('dialog [role=log] article').length === 1 && !document.querySelector('dialog [role=log]').textContent.includes('Consulta durante cierre')`))
await B.enter()
check('Reintento tras reapertura', await releaseAssistantCall(7, 'Consulta durante cierre', 200))
check('Respuesta nueva tras reapertura', await B.ev(`new Promise(resolve => { const deadline = Date.now() + 6000; const poll = () => { if (document.querySelectorAll('dialog [role=log] article').length === 2 && !document.querySelector('${editor}').readOnly) resolve(true); else if (Date.now() > deadline) resolve(false); else setTimeout(poll, 50) }; poll() })`))
await B.escape()


const cohortSelect = '#floating-assistant-cohort'
await B.ev(`document.querySelector('${launch}').click()`)
check('Teacher can select both authorized cohorts', await B.ev(`(() => {
  const options = Array.from(document.querySelector('${cohortSelect}').options, option => option.value)
  return options.includes('COH-IA') && options.includes('COH-DATA')
})()`))
check('Selecting a cohort clears the previous conversation', await B.set(cohortSelect, 'COH-IA') &&
  await B.ev("!document.querySelector('dialog [role=log] article')"))
await B.set(editor, 'Consulta de la cohorte IA')
await B.ev(`document.querySelector('${editor}').focus()`)
await B.enter()
check('Request carries the selected cohort', await releaseAssistantCall(8, 'Consulta de la cohorte IA', 200, 'COH-IA'))
check('Scoped answer is visible', await B.waitText('No consta en la documentación'))
check('Switching cohorts clears the scoped answer', await B.set(cohortSelect, 'COH-DATA') &&
  await B.ev("!document.querySelector('dialog [role=log] article')"))
await B.set(editor, 'Consulta de otra sesión')
await B.ev(`document.querySelector('${editor}').focus()`)
await B.enter()
check('New scope holds its own request', await B.ev(`document.querySelector('${editor}').readOnly`))
await B.ev("document.querySelector('[aria-label=\"Cerrar sesión\"]').click()")
check('Ending the session removes the widget', await B.waitText('Iniciar sesión') &&
  await B.ev(`!document.querySelector('${launch}')`))
check('Release the old session response', await releaseAssistantCall(9, 'Consulta de otra sesión', 200, 'COH-DATA'))
await B.login('coder-01@example.test')
check('The learner can start with a clean widget', await B.waitText('Asistente') &&
  await B.ev(`document.querySelector('${launch}')?.click(); !!document.querySelector('dialog[open]')`) &&
  await B.ev(`!document.querySelector('dialog [role=log] article') && document.querySelector('${editor}').value === '' && document.querySelector('${cohortSelect}').value === ''`))
check('No uncaught browser exceptions', errors.length === 0)
} catch (error) {
  check('Assistant widget journey', false, error.message)
} finally {
  finish()
}
