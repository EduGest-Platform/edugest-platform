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

async function checkTabOrder(page, start, next) {
  requireCheck(`Can focus ${start}`, await page.ev(`(() => {
    const field = document.querySelector(${JSON.stringify(start)})
    field?.focus()
    return !!field && document.activeElement === field
  })()`))
  await page.tab()
  requireCheck(`Tab moves visible focus from ${start} to ${next}`, await page.ev(
    `document.activeElement?.matches(${JSON.stringify(`${next}:focus-visible`)}) === true`,
  ))
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
  const localOnlyName = `Local-only application ${Date.now()}`
  const demoStorageKey = 'gistar-demo-v2'
  const seededLocalApplication = await staff.ev(`(() => {
    const key = ${JSON.stringify(demoStorageKey)}
    const demo = JSON.parse(localStorage.getItem(key) ?? 'null')
    if (!demo?.candidaturas?.length) return false
    demo.candidaturas[0].nombre_ficticio = ${JSON.stringify(localOnlyName)}
    localStorage.setItem(key, JSON.stringify(demo))
    return true
  })()`)
  await staff.goto(web)
  const retainedLocalApplication = await staff.ev(`(() => {
    const demo = JSON.parse(localStorage.getItem(${JSON.stringify(demoStorageKey)}) ?? 'null')
    return demo?.candidaturas?.some((application) => application.nombre_ficticio === ${JSON.stringify(localOnlyName)}) === true
  })()`)
  requireCheck('Local-only application survives reload', seededLocalApplication && retainedLocalApplication)
  await checkTabOrder(staff, '#lg-email', '#lg-pass')
  await staff.login('captacion.ia@gistar.example')
  requireCheck('Staff login succeeded', await waitFor(staff, "!!document.querySelector('nav') && !document.querySelector('#lg-email')"))
  requireCheck('Staff navigation', await staff.nav('Candidaturas'))
  requireCheck('Staff application list loaded', await staff.waitText('en tu ámbito'))

  const applicationList = "document.querySelector('main')"
  requireCheck('API applications exclude the local-only application', await waitFor(staff,
    `!!${applicationList}?.querySelector('tbody tr') && !${applicationList}?.innerText.includes(${JSON.stringify(localOnlyName)})`,
  ))

  await checkTabOrder(staff, '#application-search', '#application-call')
  await checkTabOrder(staff, '#application-call', '#application-stage')

  await applicant.goto(web)
  await applicant.blockUrls(['*/api/v1/calls*'])
  requireCheck('Public registration available', await applicant.click('Quiero inscribirme'))
  requireCheck('Call catalogue reports a connection failure', await applicant.waitText('No se pudo conectar con el servidor.'))
  await applicant.blockUrls([])
  requireCheck('Call catalogue can be retried', await applicant.click('Volver a cargar convocatorias'))
  requireCheck('IA call available', await waitFor(applicant, `!!document.querySelector('#ins-call option[value="CONV-IA-2027A"]')`))
  await checkTabOrder(applicant, '#ins-call', '#ins-name')
  await checkTabOrder(applicant, '#ins-name', '#ins-email')
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

  const dossierButton = "document.querySelector('main tbody tr button')"
  requireCheck('Dossier trigger can receive focus', await staff.ev(`(() => {
    const button = ${dossierButton}
    button?.focus()
    if (!button || document.activeElement !== button) return false
    button.click()
    return true
  })()`))
  requireCheck('Opening the dossier moves focus into the dialog', await waitFor(staff,
    "document.querySelector('[role=dialog]')?.contains(document.activeElement)",
  ))
  await staff.escape()
  requireCheck('Escape closes the dossier and restores focus', await waitFor(staff,
    `!document.querySelector('[role=dialog]') && document.activeElement === ${dossierButton}`,
  ))
  await staff.ev(`${dossierButton}.click()`)
  requireCheck('Persisted dossier opens', await staff.waitText('Historial CRM'))
  requireCheck('Dossier dialog has a name and a description from the synthetic registration', await staff.ev(`(() => {
    const dialog = document.querySelector('[role=dialog]')
    if (!dialog) return false
    const title = document.getElementById(dialog.getAttribute('aria-labelledby') ?? '')
    const description = document.getElementById(dialog.getAttribute('aria-describedby') ?? '')
    return !!title && !!description && title !== description
      && dialog.contains(title) && dialog.contains(description)
      && title.textContent.includes('Persona E2E Sintética')
      && description.textContent.includes(${JSON.stringify(email)})
  })()`))
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


  // KAN-184: actual unanswered contacts drive an early warning, never a stage change.
  const eventPath = `/applications/${applicationId}/events`
  const originalStage = (await authorized(`/applications/${applicationId}`, adminToken)).stage
  await authorized(eventPath, adminToken, 'POST', { tipo: 'contacto', canal: 'telefono', resultado: 'respondida', resumen: 'Synthetic reset before silence warning' })
  const policy = await authorized('/calls/CONV-IA-2027A/preselection-policy', adminToken)
  for (let i = 0; i < policy.silence_warning_contacts; i++) await authorized(eventPath, adminToken, 'POST', {
    tipo: 'contacto', canal: 'telefono', resultado: 'sin_respuesta', resumen: 'Synthetic unanswered contact',
  })
  requireCheck('Close dossier before viewing call alerts', await staff.click('Cerrar'))
  requireCheck('Select call for scoped silence alerts', await staff.set('#application-call', 'CONV-IA-2027A'))
  const alertRow = `[data-silence-application="${applicationId}"]`
  requireCheck('Persisted contacts produce a visible early warning', await waitFor(staff,
    `document.querySelector(${JSON.stringify(alertRow)})?.innerText.includes('Aviso temprano de contacto')`))
  requireCheck('Alert offers the scoped dossier', await staff.ev(`(() => { const button = document.querySelector(${JSON.stringify(alertRow + ' button')}); if (!button) return false; button.click(); return true })()`))
  requireCheck('Alert opens the correct dossier', await staff.waitText('Historial CRM'))
  requireCheck('Alert dossier matches synthetic applicant', (await staff.text()).includes(email))
  requireCheck('Close alert dossier', await staff.click('Cerrar'))
  requireCheck('Reading warning does not change application stage', (await authorized(`/applications/${applicationId}`, adminToken)).stage === originalStage)
  await authorized(eventPath, adminToken, 'POST', { tipo: 'contacto', canal: 'telefono', resultado: 'respondida', resumen: 'Synthetic response clears warning' })
  requireCheck('Refresh silence evidence', await staff.click('Actualizar alertas'))
  requireCheck('Responded contact clears warning on refresh', await waitFor(staff,
    `!document.querySelector(${JSON.stringify(alertRow)}) && !!document.querySelector('[data-silence-review]') && !document.querySelector('[data-silence-review]').innerText.includes('Cargando')`))


  // Independent staff session: search must not expose this other-program application.
  const foreign = await newBrowser()
  await foreign.goto(web)
  requireCheck('Foreign staff sign-in form is ready', await waitFor(foreign,
    "!!document.querySelector('#lg-email option[value=\"captacion.data@gistar.example\"]') && !!document.querySelector('#lg-pass')",
  ))
  requireCheck('Foreign staff account can be selected', await foreign.set('#lg-email', 'captacion.data@gistar.example'))
  requireCheck('Foreign staff password can be entered', await foreign.set('#lg-pass', process.env.GISTAR_DEMO_PASSWORD))
  requireCheck('Foreign staff sign-in can be submitted', await foreign.click('Entrar'))
  requireCheck('Foreign staff login succeeded', await waitFor(foreign, "!!document.querySelector('nav') && !document.querySelector('#lg-email')"))
  requireCheck('Foreign staff list available', await foreign.nav('Candidaturas'))
  requireCheck('Foreign staff list loaded', await foreign.waitText('en tu ámbito'))
  await foreign.set('[aria-label="Buscar expedientes"]', email)
  requireCheck('Foreign scope cannot discover dossier', await foreign.waitText('No hay expedientes con estos filtros'))
  requireCheck('Select foreign call for denied silence read', await foreign.set('#application-call', 'CONV-IA-2027A'))
  requireCheck('Foreign silence access is explicitly denied, never treated as empty', await waitFor(foreign,
    `document.querySelector('[data-silence-review]')?.innerText.includes('No tienes permiso') && !document.querySelector('[data-silence-review] [data-silence-application]')`))
  requireCheck('No browser runtime exceptions', errors.length === 0)
} catch (error) {
  // Fixed allowlist: never print arbitrary messages, names, bodies or tokens.
  const kind = error instanceof TypeError ? 'TypeError' : error instanceof Error ? 'Error' : 'Unknown'
  console.error(`Journey failure category: ${kind}`)
  check('Journey aborted: inspect preceding failed assertion (no request bodies or tokens logged)', false)
}
finish()
