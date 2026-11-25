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

try {
  const page = await newBrowser()
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
  requireCheck('No uncaught browser exceptions', errors.length === 0)
} catch (error) {
  check('Coordination dashboard journey completes', false, error instanceof Error ? error.message : 'Unknown error')
} finally {
  finish()
}
