/** KAN-246: two independent program scopes and a second collaborator in the same scope. */
const web = new URL(process.env.WEB_URL ?? 'http://localhost:8443/')
if (web.protocol !== 'http:' || !['localhost', '127.0.0.1'].includes(web.hostname) ||
    web.username || web.password || web.pathname !== '/' || web.search || web.hash) {
  throw new Error('Local synthetic HTTP origin required')
}
if (!process.env.GISTAR_DEMO_PASSWORD) throw new Error('Set the synthetic demo password')

const { newBrowser, check, errors, finish } = await import('./cdp.mjs')
const runId = crypto.randomUUID().slice(0, 8)
const board = 'document.querySelector("main")'

function requireCheck(label, result) {
  check(label, Boolean(result))
  if (!result) throw new Error(label)
}

async function setLabeled(page, label, value) {
  const fieldId = await page.ev(`Array.from(document.querySelectorAll('main label')).find(label => label.textContent.trim() === ${JSON.stringify(label)})?.htmlFor`)
  return fieldId && await page.set(`[id=${JSON.stringify(fieldId)}]`, value)
}

async function openBoard(email, programId) {
  const page = await newBrowser()
  await page.goto(web.href)
  await page.login(email)
  requireCheck(`Open the board for ${programId}`, await page.nav('Tablero de programas') &&
    await page.waitText('Asunto del nuevo hilo'))
  requireCheck(`See only the ${programId} program option`,
    await page.ev(`JSON.stringify(Array.from(document.querySelector('#discussion-program').options, option => option.value)) === ${JSON.stringify(JSON.stringify([programId]))}`))
  return page
}

async function createThread(page, subject, body) {
  requireCheck('Create a scoped thread', await setLabeled(page, 'Asunto del nuevo hilo', subject) &&
    await page.click('Crear hilo', board) && await page.waitText('Nuevo comentario'))
  requireCheck('Persist a synthetic comment', await setLabeled(page, 'Nuevo comentario', body) &&
    await page.click('Enviar comentario', board) && await page.waitText(body))
}

try {
  const ia = await openBoard('captacion.ia@gistar.example', 'P-IA')
  const data = await openBoard('captacion.data@gistar.example', 'P-DATA')
  const sameProgram = await openBoard('captacion.ia@gistar.example', 'P-IA')

  const iaSubject = `Hilo sintético IA ${runId}`
  const iaComment = `Comentario interno IA ${runId} <img data-kan244-xss src="data:,invalid" onerror="window.kan244Marker=true">`
  const dataSubject = `Hilo sintético Data ${runId}`
  const dataComment = `Comentario interno Data ${runId}`
  await createThread(ia, iaSubject, iaComment)
  await createThread(data, dataSubject, dataComment)

  requireCheck('Same-program collaborator sees an update after refreshing', await sameProgram.click('Actualizar hilos', board) &&
    await sameProgram.waitText('Novedades') && await sameProgram.waitText(iaSubject))
  const threadId = await sameProgram.ev(`Array.from(document.querySelectorAll('main select option')).find(option => option.textContent.startsWith(${JSON.stringify(iaSubject)}))?.value`)
  requireCheck('Same-program collaborator reads the shared comment', await setLabeled(sameProgram, 'Hilo', threadId) &&
    await sameProgram.waitText(iaComment))
  requireCheck('Stored markup remains text in both authorized program sessions', await ia.ev("!document.querySelector('[data-kan244-xss]') && window.kan244Marker !== true") && await sameProgram.ev("!document.querySelector('[data-kan244-xss]') && window.kan244Marker !== true"))
  await data.click('Actualizar hilos', board)
  await ia.click('Actualizar hilos', board)
  requireCheck('Data refresh retains only Data conversations', await data.waitText(dataSubject) &&
    !(await data.text()).includes(iaSubject) && !(await data.text()).includes(iaComment))
  requireCheck('IA refresh retains only IA conversations', await ia.waitText(iaSubject) &&
    !(await ia.text()).includes(dataSubject) && !(await ia.text()).includes(dataComment))
  const dataThreadId = await data.ev(`Array.from(document.querySelectorAll('main select option')).find(option => option.textContent.startsWith(${JSON.stringify(dataSubject)}))?.value`)
  requireCheck('Both programs have distinct thread identifiers', Boolean(threadId && dataThreadId && threadId !== dataThreadId))
  requireCheck('Data thread selector excludes IA thread identifier',
    await data.ev(`!Array.from(document.querySelectorAll('main select option')).some(option => option.value === ${JSON.stringify(threadId)})`))
  requireCheck('IA thread selector excludes Data thread identifier',
    await ia.ev(`!Array.from(document.querySelectorAll('main select option')).some(option => option.value === ${JSON.stringify(dataThreadId)})`))
  requireCheck('Same-program session excludes Data thread identifier',
    await sameProgram.ev(`!Array.from(document.querySelectorAll('main select option')).some(option => option.value === ${JSON.stringify(dataThreadId)})`))
  const updateMarker = `Array.from(document.querySelectorAll('main select option')).some(option =>
    option.value === ${JSON.stringify(threadId)} && option.textContent.endsWith(' · Novedades'))`
  const refresh = "Array.from(document.querySelectorAll('main button')).find(button => button.textContent === 'Actualizar hilos')"
  await ia.ev(`${refresh}.focus()`)
  requireCheck('Refreshing keeps the board control focused', await ia.click('Actualizar hilos', board) &&
    await ia.waitText(iaComment) && await ia.ev(`${refresh} === document.activeElement`))
  requireCheck('Own comment is not marked unread', !await ia.ev(updateMarker))

  const colleagueComment = `Comentario de otra sesión ${runId}`
  requireCheck('A second session adds a comment', await setLabeled(sameProgram, 'Nuevo comentario', colleagueComment) &&
    await sameProgram.click('Enviar comentario', board) && await sameProgram.waitText(colleagueComment))
  const concurrentOwnComment = `Comentario propio posterior ${runId}`
  requireCheck('The first session can add its own comment after the unseen write',
    await setLabeled(ia, 'Nuevo comentario', concurrentOwnComment) &&
    await ia.click('Enviar comentario', board) && await ia.waitText(concurrentOwnComment))
  requireCheck('Own write does not hide an intervening update', await ia.click('Actualizar hilos', board) &&
    await ia.waitText('hilos con novedades en esta página') && await ia.ev(updateMarker))
  requireCheck('The reader can clear the marker after viewing the thread',
    await ia.click('Marcar hilo como leído', board) && !await ia.ev(updateMarker))

  requireCheck('No uncaught browser errors', errors.length === 0)
} catch (error) {
  check('Program board isolation journey', false, error.message)
} finally {
  finish()
}
