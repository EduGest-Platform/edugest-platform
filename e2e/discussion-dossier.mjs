/** KAN-74 / KAN-235: keyboard focus and conflict recovery in a disposable dossier. */
const web = new URL(process.env.WEB_URL ?? 'http://localhost:8443/')
const api = new URL(process.env.GISTAR_API ?? 'http://localhost:8000')
for (const url of [web, api]) {
  if (url.protocol !== 'http:' || !['localhost', '127.0.0.1'].includes(url.hostname) ||
      url.username || url.password || url.pathname !== '/' || url.search || url.hash) {
    throw new Error('Local synthetic HTTP origins required')
  }
}
const password = process.env.GISTAR_DEMO_PASSWORD
if (!password) throw new Error('Set the synthetic demo password')

const { newBrowser, check, errors, finish, sleep } = await import('./cdp.mjs')
const dialog = "document.querySelector('[role=dialog]')"
const scope = `[...${dialog}.querySelectorAll('details')].find(item => item.querySelector('summary')?.textContent === 'Comentarios internos')`

function requireCheck(label, result) {
  check(label, Boolean(result))
  if (!result) throw new Error('Discussion assertion failed')
}

async function waitFor(page, expression) {
  for (let attempt = 0; attempt < 50; attempt++) {
    const value = await page.ev(expression)
    if (value) return value
    await sleep(200)
  }
  return null
}

async function post(path, body, expected) {
  const response = await fetch(new URL(`/api/v1${path}`, api), {
    method: 'POST', redirect: 'error', signal: AbortSignal.timeout(10000),
    headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
  })
  if (response.status !== expected) throw new Error('Unexpected fixture response')
  return response.json()
}

async function openDiscussion(page, code) {
  await page.goto(web.href)
  await page.login('captacion.ia@gistar.example')
  requireCheck('Recruiter opens applications', await page.nav('Candidaturas'))
  requireCheck('Find the dedicated synthetic dossier', await page.set('#application-search', code))
  await waitFor(page, `document.querySelector('main tbody')?.textContent.includes(${JSON.stringify(code)})`)
  requireCheck('Open only the fixture dossier', await page.ev(`(() => {
    const row = [...document.querySelectorAll('main tbody tr')].find(row => row.textContent.includes(${JSON.stringify(code)}))
    if (!row) return false
    row.querySelector('button').click()
    return true
  })()`))
  requireCheck('Discussion disclosure is reachable', await waitFor(page, `!!${dialog} && !!(${scope})`))
  await page.ev(`(() => { const summary = (${scope}).querySelector('summary'); summary.click(); summary.focus() })()`)
  requireCheck('Discussion form loads', await page.waitText('Asunto del nuevo hilo'))
}

async function setDiscussionField(page, label, value) {
  const id = await page.ev(`[...(${scope}).querySelectorAll('label')].find(item => item.textContent.trim() === ${JSON.stringify(label)})?.htmlFor`)
  return id && await page.set(`[id=${JSON.stringify(id)}]`, value)
}

async function draftIs(page, value) {
  return page.ev(`(${scope})?.querySelector('textarea')?.value === ${JSON.stringify(value)}`)
}

try {
  const receipt = await post('/applications', {
    call_id: 'CONV-IA-2027A', nombre: 'Expediente sintético de comentarios',
    email: `discussion.${Date.now()}@example.test`, motivacion: 'Solicitud sintética para probar discusiones internas.',
    disponibilidad: 'Flexible', acepta_datos_sinteticos: true,
  }, 201)
  const first = await newBrowser()
  const second = await newBrowser()
  await openDiscussion(first, receipt.codigo)
  await first.tab()
  requireCheck('Tab moves focus to the labelled subject field', await first.ev(`(() => {
    const field = document.activeElement
    return field?.tagName === 'INPUT' && field.labels?.[0]?.textContent.trim() === 'Asunto del nuevo hilo'
  })()`))
  const subject = 'Hilo sintético <img data-kan244-xss src="data:,invalid">'
  requireCheck('Write a thread subject', await setDiscussionField(first, 'Asunto del nuevo hilo', subject))
  requireCheck('Create the thread', await first.click('Crear hilo', `(${scope})`))
  requireCheck('New thread is selected', await first.waitText('Nuevo comentario'))
  requireCheck('Thread subject is literal text in the selector', await first.ev(`Array.from((${scope}).querySelectorAll('option')).some(option => option.textContent === ${JSON.stringify(subject)})`))
  const original = 'Texto literal <img data-kan244-xss src="data:,invalid" onerror="window.kan244Marker=true">'
  requireCheck('Write the first comment', await setDiscussionField(first, 'Nuevo comentario', original))
  requireCheck('Save the first comment', await first.click('Enviar comentario', `(${scope})`))
  requireCheck('Comment is displayed as literal text', await first.waitText(original))
  requireCheck('Stored markup does not create a DOM node or run an event handler', await first.ev("!document.querySelector('[data-kan244-xss]') && window.kan244Marker !== true"))
  requireCheck('Reply points to the visible parent', await first.click('Responder', `(${scope})`))
  requireCheck('Reply focuses its textarea', await first.ev(`document.activeElement?.matches('textarea') && !!(${scope})?.contains(document.activeElement)`))
  const reply = 'Respuesta sintética <img data-kan244-xss src="data:,invalid" onerror="window.kan244Marker=true">'
  requireCheck('Write and save a reply', await setDiscussionField(first, 'Tu respuesta', reply) &&
    await first.click('Enviar respuesta', `(${scope})`))
  requireCheck('Reply appears below its parent as text', await first.waitText(reply))
  requireCheck('Reply markup cannot create nodes or execute', await first.ev("!document.querySelector('[data-kan244-xss]') && window.kan244Marker !== true"))

  await openDiscussion(second, receipt.codigo)
  requireCheck('Second browser loads the same comment and reply', await second.waitText(original) && await second.waitText(reply))
  requireCheck('Persisted markup remains inert in a fresh browser session', await second.ev("!document.querySelector('[data-kan244-xss]') && window.kan244Marker !== true"))
  requireCheck('First browser starts an edit', await first.click('Editar comentario', `(${scope})`))
  const draft = 'Borrador que debe conservarse'
  requireCheck('First browser changes its draft', await setDiscussionField(first, 'Editar tu comentario', draft))
  requireCheck('Second browser edits the same comment', await second.click('Editar comentario', `(${scope})`))
  requireCheck('Second browser saves a newer version', await setDiscussionField(second, 'Editar tu comentario', 'Revisión nueva de la otra pestaña') &&
    await second.click('Guardar edición', `(${scope})`))
  requireCheck('New version persisted', await second.waitText('Revisión nueva de la otra pestaña'))

  requireCheck('First browser sends its observed version', await first.click('Guardar edición', `(${scope})`))
  requireCheck('Conflict is announced and draft kept', await first.waitText('Hay una revisión nueva') && await draftIs(first, draft))
  requireCheck('Refresh fetches the current version', await first.click('Actualizar hilo', `(${scope})`) &&
    await first.waitText('Versión actual del comentario'))
  requireCheck('Refresh keeps the draft and blocks blind overwrite', await draftIs(first, draft) &&
    await first.ev(`[...(${scope}).querySelectorAll('button')].find(item => item.textContent.trim() === 'Guardar edición')?.disabled === true`))
  requireCheck('Explicitly adopt the current revision', await first.click('Conservar mi borrador y usar esta versión', `(${scope})`))
  requireCheck('Save the retained draft', await first.click('Guardar edición', `(${scope})`) && await first.waitText('Comentario actualizado.'))
  requireCheck('Resolve and reopen the thread', await first.click('Resolver hilo', `(${scope})`) && await first.waitText('Hilo resuelto.') &&
    await first.click('Reabrir hilo', `(${scope})`) && await first.waitText('Hilo reabierto.'))

  const outsider = await post('/auth/login', { email: 'captacion.data@gistar.example', password }, 200)
  const outOfScope = new URL('/api/v1/discussion-threads', api)
  outOfScope.search = new URLSearchParams({ scope_type: 'application', application_id: receipt.id })
  const denied = await fetch(outOfScope, {
    signal: AbortSignal.timeout(10000), headers: { Authorization: `Bearer ${outsider.access_token}` },
  })
  requireCheck('API denies access outside the authorized scope', denied.status === 403)
  requireCheck('Browser reports no uncaught exceptions', errors.length === 0)
} catch {
  check('Discussion browser journey completed', false)
} finally {
  finish()
}
