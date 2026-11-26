/** KAN-186: protect in-progress edits and writes in the server competency workspace. */
const web = new URL(process.env.WEB_URL ?? 'http://127.0.0.1:8443/')
for (const url of [web, new URL(process.env.GISTAR_API ?? 'http://127.0.0.1:8000')]) {
  if (url.protocol !== 'http:' || !['127.0.0.1', 'localhost'].includes(url.hostname) ||
      url.username || url.password || url.pathname !== '/' || url.search || url.hash) {
    throw new Error('Local synthetic HTTP origins required')
  }
}
if (!process.env.GISTAR_DEMO_PASSWORD) throw new Error('Set the synthetic demo password')

const { newBrowser, check, errors, finish, sleep } = await import('./cdp.mjs')

async function waitFor(page, expression) {
  for (let attempt = 0; attempt < 60; attempt++) {
    if (await page.ev(expression)) return true
    await sleep(100)
  }
  return false
}

function requireCheck(label, ok) {
  check(label, Boolean(ok))
  if (!ok) throw new Error(label)
}

const selectorsLocked = `document.querySelector('#competency-cohort')?.disabled
  && document.querySelector('#competency-learner')?.disabled
  && [...document.querySelectorAll('main button')].some(button =>
    button.textContent.trim() === 'Actualizar cohorte' && button.disabled)`

try {
  const page = await newBrowser()
  await page.initScript(`(() => {
    const original = window.fetch.bind(window);
    window.fetch = async (request, options) => {
      const path = new URL(request instanceof Request ? request.url : String(request), location.href).pathname;
      const response = await original(request, options);
      if (response.ok && path.endsWith('/competency-roster')) {
        const roster = await response.json();
        for (const row of roster.items.slice(0, 2)) row.display_name = 'Nombre sintético repetido';
        return new Response(JSON.stringify(roster), { headers: { 'Content-Type': 'application/json' } });
      }
      if (response.ok && request.method === 'POST' && /\\/(assessments|competency-frameworks)$/.test(path)) {
        await new Promise(release => { window.releaseCompetencyWrite = release; });
        delete window.releaseCompetencyWrite;
      }
      return response;
    };
  })()`)
  await page.goto(web.href)
  await page.login('docente@gistar.example')
  requireCheck('Opens the API Rúbricas view with the matching heading', await page.nav('Rúbricas')
    && await waitFor(page, "document.querySelector('main h1')?.textContent === 'Rúbricas'"))
  requireCheck('Loads the synthetic cohort roster', await waitFor(page, "Boolean(document.querySelector('#competency-learner option:nth-child(3)'))"))
  const duplicateLabels = await page.ev(`[...document.querySelectorAll('#competency-learner option')].slice(1, 3)
    .map(item => ({ id: item.value, label: item.textContent }))`)
  requireCheck('Duplicate names display different enrollment references', duplicateLabels.length === 2
    && duplicateLabels.every(item => item.label.startsWith('Nombre sintético repetido · matrícula '))
    && duplicateLabels[0].label !== duplicateLabels[1].label)

  const learner = duplicateLabels[0]
  await page.set('#competency-learner', learner.id)
  requireCheck('Shows the selected learner and reference beside the assessment', await page.waitText('Matrícula seleccionada: ' + learner.label))
  requireCheck('Assessment evidence locks context selection and refresh', await waitFor(page,
    "Boolean(document.querySelector('#assessment-evidence'))") && await page.set('#assessment-evidence', 'Evidencia sintética de revisión')
    && await page.ev(selectorsLocked))
  requireCheck('Saves assessment through the real API', await page.click('Guardar evaluación')
    && await waitFor(page, "typeof window.releaseCompetencyWrite === 'function'"))
  requireCheck('The server has responded and context stays locked until completion', await page.ev(selectorsLocked))
  await page.ev('window.releaseCompetencyWrite()')
  requireCheck('Shows the saved assessment and unlocks selection', await page.waitText('Evaluación guardada.')
    && await page.waitText('Evidencia sintética de revisión') && await page.ev("!document.querySelector('#competency-cohort').disabled"))

  requireCheck('Opens the framework editor', await page.click('Crear borrador'))
  await page.set('[id$="-nombre"]', 'Competencia sintética de revisión')
  for (const level of [1, 2, 3]) await page.set(`[id$="-level_${level}"]`, 'Evidencia del nivel ' + level)
  requireCheck('Editing a framework blocks refresh and selection', await page.ev(selectorsLocked))
  requireCheck('Saving a framework also blocks selection until the API result arrives', await page.click('Guardar borrador')
    && await waitFor(page, "typeof window.releaseCompetencyWrite === 'function'")
    && await page.ev(selectorsLocked))
  await page.ev('window.releaseCompetencyWrite()')
  requireCheck('Reopens the saved draft', await page.waitText('Borrador guardado.')
    && await waitFor(page, "[...document.querySelectorAll('main button')].some(button => button.textContent.trim() === 'Editar borrador' && !button.disabled)")
    && await page.click('Editar borrador'))
  requireCheck('Cannot reopen or switch drafts with unsaved edits', await page.set('[id$="-nombre"]', 'Cambios todavía sin guardar')
    && await page.ev(`[...document.querySelectorAll('main button')].filter(button => button.textContent.trim() === 'Editar borrador')
      .every(button => button.disabled) && document.querySelector('[id$="-nombre"]').value === 'Cambios todavía sin guardar'`))
  requireCheck('Explicitly cancels the edit and releases the lock', await page.click('Cancelar edición')
    && await page.ev("!document.querySelector('#competency-cohort').disabled"))
  requireCheck('No uncaught browser exceptions', errors.length === 0)
} catch (error) {
  check('Competency workspace journey', false, error.message)
} finally {
  finish()
}
