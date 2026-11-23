/** KAN-140: repeatable F1 browser journey on disposable synthetic services. */
const web = process.env.WEB_URL ?? 'http://localhost:8443/'
const api = process.env.GISTAR_API ?? 'http://localhost:8000'
for (const value of [web, api]) {
  const url = new URL(value)
  if (!['localhost', '127.0.0.1'].includes(url.hostname)) throw new Error('Local synthetic services required')
}
if (!process.env.GISTAR_DEMO_PASSWORD) throw new Error('Set the synthetic demo password')
const fixture = process.env.E2E_FIXTURE_ID ?? 'local-f1-registration'
if (!/^[a-zA-Z0-9-]{1,64}$/.test(fixture)) throw new Error('Invalid synthetic fixture identifier')
const email = `e2e.${fixture.toLowerCase()}@example.test`
const { newBrowser, check, errors, finish, sleep } = await import('./cdp.mjs')

function requireCheck(name, ok) {
  check(name, Boolean(ok))
  if (!ok) throw new Error(name)
}

async function waitFor(page, expression, timeout = 10000) {
  for (let elapsed = 0; elapsed < timeout; elapsed += 200) {
    if (await page.ev(expression)) return true
    await sleep(200)
  }
  return false
}

async function submit(page, value) {
  requireCheck('Synthetic name field exists', await page.set('#ins-name', 'Persona E2E Sintética'))
  await page.set('#ins-email', value)
  await page.set('#ins-mot', 'Motivación sintética reproducible para comprobar el recorrido F1.')
  await page.ev(`(() => { const e = document.querySelector('form input[type=checkbox]'); if (!e.checked) e.click() })()`)
  requireCheck('Registration submitted', await page.click('Enviar candidatura'))
  requireCheck('Registration result received', await waitFor(page, `document.body.innerText.includes('Candidatura recibida') || document.body.innerText.includes('Ya existe una candidatura')`))
}

try {
  const staff = await newBrowser()
  const applicant = await newBrowser()
  await staff.goto(web)
  requireCheck('API login screen', await staff.waitText('Iniciar sesión'))
  await staff.login('captacion.ia@gistar.example')
  requireCheck('Staff login succeeded', await waitFor(staff, "!!document.querySelector('nav') && !document.querySelector('#lg-email')"))
  requireCheck('Staff navigation', await staff.nav('Candidaturas'))
  requireCheck('Staff application list loaded', await staff.waitText('en tu ámbito'))

  await applicant.goto(web)
  requireCheck('Public registration available', await applicant.click('Quiero inscribirme'))
  requireCheck('IA call available', await waitFor(applicant, `!!document.querySelector('#ins-call option[value="CONV-IA-2027A"]')`))
  await applicant.set('#ins-call', 'CONV-IA-2027A')
  await submit(applicant, email)
  // A repeat run may find this fixture already present. It must still find exactly one persisted dossier.
  const created = (await applicant.text()).includes('Candidatura recibida')
  if (created) {
    requireCheck('Repeat submission available', await applicant.click('Enviar otra candidatura'))
    await waitFor(applicant, `!!document.querySelector('#ins-call')`)
    await applicant.set('#ins-call', 'CONV-IA-2027A')
    await submit(applicant, email.toUpperCase())
  }
  requireCheck('Duplicate rejected without creating another application', await applicant.waitText('Ya existe una candidatura'))

  await staff.set('[aria-label="Buscar expedientes"]', email)
  requireCheck('Exactly one shared dossier visible', await waitFor(staff, `document.querySelectorAll('main tbody tr').length === 1 && document.querySelector('main tbody tr').innerText.includes(${JSON.stringify(email)})`))
  requireCheck('Dossier belongs to IA call', await staff.ev("document.querySelector('main tbody tr')?.innerText.includes('CONV-IA-2027A')"))
  await staff.goto(web)
  requireCheck('Staff session survives browser reload', await waitFor(staff, "!!document.querySelector('nav') && !document.querySelector('#lg-email')"))
  requireCheck('Staff can reopen applications after reload', await staff.nav('Candidaturas'))
  requireCheck('Reloaded application list is available', await staff.waitText('en tu ámbito'))
  requireCheck('Staff can search for the dossier after reload', await staff.set('[aria-label="Buscar expedientes"]', email))
  requireCheck('Exactly one dossier remains visible after reload', await waitFor(staff,
    `document.querySelectorAll('main tbody tr').length === 1 && document.querySelector('main tbody tr').innerText.includes(${JSON.stringify(email)})`,
  ))

  await staff.ev(`document.querySelector('main tbody tr button').click()`)
  requireCheck('Persisted dossier opens', await staff.waitText('Historial CRM'))
  requireCheck('Dossier contains synthetic registration', (await staff.text()).includes(email))

  // KAN-145: real authorized requirement reads, explicit versions and a refreshed human review.
  async function authorized(path, token, method = 'GET', body) {
    const response = await fetch(`${api}/api/v1${path}`, {
      method, headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body),
    })
    if (!response.ok) throw new Error(`Synthetic requirement fixture failed: ${method} ${response.status}`)
    return response.json()
  }
  const loginResponse = await fetch(`${api}/api/v1/auth/login`, { method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: 'admin@gistar.example', password: process.env.GISTAR_DEMO_PASSWORD }) })
  if (!loginResponse.ok) throw new Error('Synthetic requirement fixture login failed')
  const adminToken = (await loginResponse.json()).access_token
  const catalogue = await authorized('/calls/CONV-IA-2027A/requirements', adminToken)
  for (const version of [1, 2]) {
    const ref = `e2e-review-v${version}`
    if (!catalogue.items.some((row) => row.ref === ref)) await authorized('/calls/CONV-IA-2027A/requirements', adminToken, 'POST', {
      ref, code: 'e2e-review', label: `Requisito E2E sintético ${version}`, kind: 'required', expected_version: version - 1,
    })
  }
  const applications = await authorized(`/applications?q=${encodeURIComponent(email)}`, adminToken)
  const applicationId = applications.items.find((row) => row.person.email === email)?.id
  if (!applicationId) throw new Error('Synthetic requirement dossier missing')
  const reviewPath = `/applications/${applicationId}/requirement-reviews`
  const previous = (await authorized(reviewPath, adminToken)).items.find((row) => row.requirement_ref === 'e2e-review-v1')
  const firstReview = await authorized(`${reviewPath}/e2e-review-v1`, adminToken, 'PUT', {
    result: 'not_met', reason: 'Synthetic E2E human review', ...(previous ? { expected_version: previous.version } : {}),
  })
  const panel = `document.querySelector('[data-server-requirements]')`
  await staff.click('Actualizar requisitos')
  requireCheck('Server requirement versions loaded', await waitFor(staff, `!!document.querySelector('#requirement-version-e2e-review')`))
  requireCheck('No latest version selected automatically', await staff.ev(`document.querySelector('#requirement-version-e2e-review').value === ''`))
  await staff.set('#requirement-version-e2e-review', 'e2e-review-v1')
  requireCheck('Persisted negative review is visible', await waitFor(staff, `${panel}?.innerText.includes('No cumple')`))
  await staff.set('#requirement-version-e2e-review', 'e2e-review-v2')
  requireCheck('Another version does not inherit the review', await waitFor(staff, `${panel}?.innerText.includes('Pendiente') && !${panel}?.innerText.includes('No cumple')`))
  await authorized(`${reviewPath}/e2e-review-v1`, adminToken, 'PUT', {
    result: 'met', reason: 'Synthetic E2E reviewed amendment', expected_version: firstReview.version,
  })
  await staff.click('Actualizar requisitos')
  await waitFor(staff, `!!document.querySelector('#requirement-version-e2e-review') && document.querySelector('#requirement-version-e2e-review').value === ''`)
  await staff.set('#requirement-version-e2e-review', 'e2e-review-v1')
  requireCheck('Refresh shows amended server review', await waitFor(staff, `${panel}?.innerText.includes('Cumple') && !${panel}?.innerText.includes('No cumple')`))


  // Independent staff session: search must not expose this other-program application.
  const foreign = await newBrowser()
  await foreign.goto(web)
  await foreign.login('captacion.data@gistar.example')
  requireCheck('Foreign staff login succeeded', await waitFor(foreign, "!!document.querySelector('nav') && !document.querySelector('#lg-email')"))
  requireCheck('Foreign staff list available', await foreign.nav('Candidaturas'))
  requireCheck('Foreign staff list loaded', await foreign.waitText('en tu ámbito'))
  await foreign.set('[aria-label="Buscar expedientes"]', email)
  requireCheck('Foreign scope cannot discover dossier', await foreign.waitText('No hay expedientes con estos filtros'))
  requireCheck('No browser runtime exceptions', errors.length === 0)
} catch (error) {
  // Fixed allowlist: never print arbitrary messages, names, bodies or tokens.
  const kind = error instanceof TypeError ? 'TypeError' : error instanceof Error ? 'Error' : 'Unknown'
  console.error(`Journey failure category: ${kind}`)
  check('Journey aborted: inspect preceding failed assertion (no request bodies or tokens logged)', false)
}
finish()
