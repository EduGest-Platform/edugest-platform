/**
 * E2E · Incremento F1 (modo API). Sin dependencias: Chromium + Chrome DevTools Protocol.
 * Requisitos: API en GISTAR_API (http://127.0.0.1:8000) con seed reciente, web compilada con
 * VITE_GISTAR_API_URL y servida en WEB_URL (http://127.0.0.1:4173). Ver docs/incrementos/F1-cimientos.md.
 * Se migrará a Playwright en F5.
 */
import { PASSWORD, check, errors, finish, newBrowser, sleep } from './cdp.mjs'

const WEB = process.env.WEB_URL ?? 'http://127.0.0.1:4173/'

const unique = `e2e.${Date.now()}@example.test`
const A = await newBrowser()
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
    await new Promise(release => window.assistantTestCalls.push({ question: body.question, status, release }))
    const data = status === 503 ? { detail: 'Synthetic unavailable' } : {
      status: 'no_source', mode: 'extractive', retrieval: 'keyword', answer: 'No consta',
      citations: [], as_of: '2026-11-26', scope_cohorts: ['COH-IA'], source_kind: 'documents', record: null,
    }
    if (status !== 200) return new Response(JSON.stringify(data), { status, headers: { 'Content-Type': 'application/json' } })
    const frame = (event, payload) => 'event: ' + event + '\\n' + 'data: ' + JSON.stringify(payload) + '\\n\\n'
    return new Response(frame('phase', { source_kind: 'documents' }) + frame('delta', { text: 'No consta' }) + frame('answer', data), { status, headers: { 'Content-Type': 'text/event-stream' } })
  }
})()`)

// 1 · A: captación IA inicia sesión y ve solo su ámbito
await A.goto(WEB)
check('Pantalla de acceso en modo API', await A.waitText('Iniciar sesión'))
await A.login('captacion.ia@gistar.example')
await A.nav('Candidaturas')
await A.waitText('en tu ámbito')
await sleep(600)
const before = await A.rows()
const callsA = await A.ev(`[...document.querySelectorAll('main tbody tr td:nth-child(3)')].map(td => td.textContent)`)
check('Captación IA ve solo expedientes de su programa', before > 0 && callsA.every((c) => c.startsWith('CONV-IA')), `filas=${before}`)

// 2 · B: inscripción pública (otro navegador, sin sesión)
await B.goto(WEB)
await B.click('Quiero inscribirme')
check('Convocatoria sintética IA disponible', await B.waitText('IA aplicada'))
await B.set('#ins-call', 'CONV-IA-2027A')
await B.set('#ins-name', 'Persona E2E Sintética')
await B.set('#ins-email', unique)
await B.set('#ins-mot', 'Motivación de prueba E2E con datos sintéticos.')
await B.ev(`document.querySelector('form input[type=checkbox]').click()`)
await B.click('Enviar candidatura')
const ok = await B.waitText('Candidatura recibida')
const code = await B.ev(`document.querySelector('main, body').innerText.match(/IA27A-\\d{4}/)?.[0] ?? null`)
check('Inscripción pública crea candidatura con código', ok && !!code, code ?? '')

// 3 · B repite el mismo correo -> 409 sin duplicar
await B.click('Enviar otra candidatura')
await sleep(400)
await B.set('#ins-name', 'Persona E2E Sintética')
await B.set('#ins-email', unique.toUpperCase())
await B.set('#ins-mot', 'Segundo intento con el mismo correo.')
await B.ev(`document.querySelector('form input[type=checkbox]').click()`)
await B.click('Enviar candidatura')
check('Duplicado en la misma convocatoria rechazado', await B.waitText('Ya existe una candidatura'))

// 4 · A ve la nueva candidatura (persistencia compartida entre navegadores)
await A.ev(`document.querySelector('[aria-label=Actualizar]').click()`)
await sleep(900)
const after = await A.rows()
check('El otro navegador ve la nueva candidatura', after === before + 1 && (await A.text()).includes(code), `filas=${after}`)

// 5 · A abre la ficha y registra un contacto CRM
await A.ev(`[...document.querySelectorAll('main tbody tr')].find(r => r.innerText.includes(${JSON.stringify(code)})).querySelector('button').click()`)
await A.waitText('Historial CRM')
await A.set('[aria-label="Resumen del evento"]', 'Llamada E2E: confirma asistencia a la jornada informativa')
await A.click('Registrar en el historial', "document.querySelector('[role=dialog]')")
check('Evento CRM registrado con autor', await A.waitText('Llamada E2E: confirma asistencia a la jornada informativa')
  && await A.ev(`[...document.querySelectorAll('[role=dialog] li')].some(item => item.textContent.includes('Llamada E2E:') && item.textContent.includes('Captación IA (demo)'))`))
await A.click('Cerrar', "document.querySelector('[role=dialog] footer')")

// 6 · B: captación Data no ve expedientes de IA
await B.goto(WEB)
await B.click('Iniciar sesión')
await sleep(300)
await B.login('captacion.data@gistar.example')
await B.nav('Candidaturas')
await B.waitText('en tu ámbito')
await sleep(600)
const dataText = await B.text()
const callsB = await B.ev(`[...document.querySelectorAll('main tbody tr td:nth-child(3)')].map(td => td.textContent)`)
check('Captación Data no ve la candidatura de IA', !dataText.includes(code) && callsB.length > 0 && callsB.every((c) => c.startsWith('CONV-DATA')))
await B.click('Salir')
await sleep(500)

// 7 · B: docente -> la API deniega expedientes (403)
await B.login('docente@gistar.example')
check('Vistas no migradas señalan datos locales', await B.waitText('datos locales de demostración'))
// KAN-268 · Floating assistant: deterministic browser responses, real keyboard events.
const editor = '[aria-label="Pregunta al asistente"]'
const launch = '[aria-label="Abrir asistente EduGest"]'

async function releaseAssistantCall(index, question, status) {
  for (let attempt = 0; attempt < 30; attempt++) {
    const recorded = await B.ev(`(() => {
      const calls = window.assistantTestCalls;
      const call = calls[${index}];
      if (calls.length !== ${index + 1} || call.question !== ${JSON.stringify(question)} || call.status !== ${status}) return false;
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

await B.nav('Candidaturas')
check('Docente recibe denegación de la API', await B.waitText('No tienes permiso para ver esta información.'))
await B.click('Salir')
await sleep(500)

// 8 · B: coordinación no tiene vista de candidaturas ni selector libre de rol
await B.login('coordinacion@gistar.example')
const coordNav = await B.ev(`[...document.querySelectorAll('nav[aria-label="Navegación principal"] button')].map(b => b.textContent).join('|')`)
const roleOptions = await B.ev(`document.querySelectorAll('#role option').length`)
check('Coordinación sin candidaturas y rol fijado por el servidor', !coordNav.includes('Candidaturas') && roleOptions === 1, `opciones=${roleOptions}`)
await B.click('Salir')
await sleep(500)

// 9 · B: administración ve la auditoría del servidor
await B.login('admin@gistar.example')
await B.nav('Auditoría')
await B.waitText('application.created')
const audit = await B.text()
check('Auditoría del servidor sin datos personales', audit.includes('application.created') && audit.includes('application.event_added') && !audit.includes(unique))

// 10 · Sesión por pestaña: A sigue con su sesión
await A.ev(`document.querySelector('[aria-label=Actualizar]').click()`)
await sleep(800)
check('La sesión de A sigue activa tras los inicios/cierres de sesión de B', (await A.rows()) === before + 1 && !(await A.text()).includes('Quiero inscribirme'))
check('Sin excepciones JS', errors.length === 0, errors.join(' | ').slice(0, 300))

finish()
