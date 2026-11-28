/** Coordination dashboard on disposable synthetic services. */
const web = new URL(process.env.WEB_URL ?? 'http://localhost:8443/')
for (const url of [web, new URL(process.env.GISTAR_API ?? 'http://localhost:8000')]) {
  if (url.protocol !== 'http:' || !['localhost', '127.0.0.1'].includes(url.hostname) || url.username || url.password) {
    throw new Error('Local synthetic HTTP origins required')
  }
}
if (!process.env.GISTAR_DEMO_PASSWORD) throw new Error('Set the synthetic demo password')

const { newBrowser, check, errors, finish, sleep } = await import('./cdp.mjs')

function requireCheck(label, ok) {
  check(label, Boolean(ok))
  if (!ok) throw new Error(label)
}

async function waitFor(page, expression) {
  for (let attempt = 0; attempt < 50; attempt++) {
    if (await page.ev(expression)) return true
    await sleep(200)
  }
  return false
}

function stageCount(stage, count) {
  return `[...document.querySelectorAll('main dt')].some(label =>
    label.textContent === ${JSON.stringify(stage)} && label.nextElementSibling?.textContent === ${JSON.stringify(count)})`
}

try {
  const page = await newBrowser()
  await page.initScript(`(() => {
    const fetchRequest = window.fetch.bind(window);
    const intake = window.manualIntakeTest = { delayCalls: false, rejectSubmission: false, summaryReads: 0 };
    window.fetch = (request, options) => {
      const path = new URL(request.url ?? request, location.href).pathname;
      if (path.endsWith('/summary')) intake.summaryReads++;
      if (path === '/api/v1/manual-intake/calls' && intake.delayCalls) {
        intake.delayCalls = false;
        return new Promise(resolve => {
          intake.releaseCalls = () => resolve(new Response('{"detail":"Stale synthetic response"}', {
            status: 503, headers: { 'Content-Type': 'application/json' },
          }));
        });
      }
      if (path === '/api/v1/manual-intake/applications' && intake.rejectSubmission) {
        intake.rejectSubmission = false;
        return Promise.reject(new TypeError('Synthetic connection loss'));
      }
      return fetchRequest(request, options);
    };
  })()`)
  await page.goto(web.href)
  await page.blockUrls(['*/api/v1/calls/*/summary'])
  await page.login('coordinacion@gistar.example')
  requireCheck('Coordination opens the server dashboard', await page.waitText('Seguimiento de convocatorias'))
  requireCheck('Failed metric request is announced', await waitFor(page,
    "document.querySelector('main [role=alert]')?.textContent.includes('No se pudo conectar con la API')"))

  await page.ev("document.querySelector('#coordination-program').focus()")
  await page.tab()
  requireCheck('Tab moves from program to call with visible focus', await page.ev(
    "document.activeElement?.matches('#coordination-call:focus-visible')"))
  await page.tab()
  requireCheck('Tab moves to Refresh indicators with visible focus', await page.ev(
    "document.activeElement?.matches('button:focus-visible') && document.activeElement.textContent.trim() === 'Actualizar indicadores'"))

  await page.blockUrls([])
  await page.click('Actualizar indicadores')
  requireCheck('Refresh recovers the failed metric request', await page.waitText('Candidaturas totales'))
  requireCheck('Refresh preserves keyboard focus', await page.ev(
    "document.activeElement?.textContent.trim() === 'Actualizar indicadores'"))

  requireCheck('Program filter can select IA', await page.set('#coordination-program', 'P-IA'))
  requireCheck('Only the selected program calls remain', await waitFor(page, `(() => {
    const options = [...document.querySelectorAll('#coordination-call option')].map(option => option.value);
    return options.length > 0 && options.every(id => id.startsWith('CONV-IA-'));
  })()`))
  requireCheck('IA totals match the synthetic fixture', await waitFor(page,
    `(() => {
      const metrics = new Map([...document.querySelectorAll('main .tabular-nums')]
        .map(value => [value.previousElementSibling?.textContent, value.textContent]));
      return metrics.get('Candidaturas totales') === '50' && metrics.get('Plazas ofertadas') === '25';
    })()`) && await waitFor(page, stageCount('enviada', '16'))
    && await waitFor(page, stageCount('convocada', '12')))
  requireCheck('Small stage count stays hidden and an actual zero remains visible',
    await waitFor(page, stageCount('admitida', 'Oculta')) && await waitFor(page, stageCount('lista espera', '0')))

  requireCheck('Empty seeded call is selectable', await page.set('#coordination-call', 'CONV-IA-2026B'))
  requireCheck('Small call hides the whole breakdown', await page.waitText('El total y el desglose se ocultan')
    && await page.ev(`!document.querySelector('main dt') && document.querySelector('main').innerText.includes('Ocultas')`))

  requireCheck('Data program can be selected', await page.set('#coordination-program', 'P-DATA'))
  requireCheck('Data totals replace IA totals', await waitFor(page, stageCount('enviada', '21'))
    && await waitFor(page, stageCount('convocada', '6'))
    && !(await page.ev(stageCount('enviada', '16'))))
  // KAN-275: a manual registration must refresh the totals on screen. Needs a freshly seeded database.
  const total = (count) => `[...document.querySelectorAll('main .tabular-nums')]
    .some(value => value.previousElementSibling?.textContent === 'Candidaturas totales' && value.textContent === '${count}')`
  requireCheck('IA programme can be selected again', await page.set('#coordination-program', 'P-IA'))
  requireCheck('Open IA call can be selected', await page.set('#coordination-call', 'CONV-IA-2027A'))
  requireCheck('Totals before the manual registration', await waitFor(page, total(50)))
  await page.ev('window.manualIntakeTest.delayCalls = true')
  requireCheck('Open the manual intake form', await page.click('Registrar candidatura'))
  requireCheck('The first call list response is held', await waitFor(page, 'Boolean(window.manualIntakeTest.releaseCalls)'))
  requireCheck('Reopen the form to start a new call list request', await page.click('Ocultar') && await page.click('Registrar candidatura'))
  const validCalls = "document.querySelectorAll('#manual-call option').length > 1"
  requireCheck('Calls load in the form', await waitFor(page, validCalls))
  await page.ev(`(async () => {
    window.manualIntakeTest.releaseCalls();
    await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
  })()`)
  requireCheck('The older response cannot replace the call list', await page.ev(validCalls))
  requireCheck('Choose call and origin', await page.set('#manual-call', 'CONV-IA-2027A') && await page.set('#manual-origin', 'telefono'))
  requireCheck('Type synthetic data', await page.set('#manual-name', 'Persona Sintética Manual')
    && await page.set('#manual-email', `manual.${Date.now()}@example.test`)
    && await page.set('#manual-motivation', 'Solicitud sintética registrada por teléfono'))
  await page.ev("document.querySelector('#manual-call').closest('form').querySelector('input[type=checkbox]').click()")
  const email = await page.ev("document.querySelector('#manual-email').value")
  const locked = "document.querySelector('#manual-name').closest('fieldset').disabled"
  await page.networkLatency(1500)
  requireCheck('Submit the manual registration', await page.click('Registrar'))
  requireCheck('The form is locked while the request is pending', await waitFor(page, locked))
  await page.networkLatency(0)
  requireCheck('The new code is shown', await page.waitText('Candidatura registrada con el código'))
  requireCheck('Totals refresh without reloading the page', await waitFor(page, total(51)))
  requireCheck('The form is cleared and unlocked', await waitFor(page,
    `document.querySelector('#manual-name').value === '' && !${locked}`))

  // The same email on the same call is refused: the draft stays, the form unlocks and focus reaches the reason.
  await page.set('#manual-origin', 'telefono')
  await page.set('#manual-name', 'Persona Sintética Repetida')
  await page.set('#manual-email', email)
  await page.set('#manual-motivation', 'Segunda solicitud sintética con el mismo correo')
  await page.ev("document.querySelector('#manual-call').closest('form').querySelector('input[type=checkbox]').click()")
  requireCheck('Submit the repeated application', await page.click('Registrar'))
  requireCheck('The refusal is announced', await page.waitText('Ya existe una candidatura'))
  requireCheck('A refusal keeps the draft and unlocks the form', await waitFor(page,
    `document.querySelector('#manual-name').value === 'Persona Sintética Repetida' && !${locked}`))
  requireCheck('Focus moves to the result', await waitFor(page, "document.activeElement?.matches('[data-intake-result]')"))
  await page.set('#manual-email', `unconfirmed.${Date.now()}@example.test`)
  const summaryReads = await page.ev('window.manualIntakeTest.summaryReads')
  await page.ev('window.manualIntakeTest.rejectSubmission = true')
  requireCheck('Submit with a simulated connection loss', await page.click('Registrar'))
  requireCheck('An unconfirmed send keeps the draft and unlocks the form', await waitFor(page,
    `document.querySelector('#manual-name').value === 'Persona Sintética Repetida' && !${locked}
      && document.querySelector('[data-intake-result]')?.textContent.includes('confirmar')`))
  requireCheck('An unconfirmed send triggers a fresh indicator read',
    await waitFor(page, `window.manualIntakeTest.summaryReads > ${summaryReads}`))
  requireCheck('No uncaught browser exceptions', errors.length === 0)
} catch (error) {
  check('Coordination dashboard journey completes', false, error instanceof Error ? error.message : 'Unknown error')
} finally {
  finish()
}
