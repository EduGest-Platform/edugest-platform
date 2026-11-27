/** KAN-232: global-admin invitation rotation, revocation and consumption in synthetic sessions. */
const web = new URL(process.env.WEB_URL ?? 'http://localhost:8443/')
if (web.protocol !== 'http:' || !['localhost', '127.0.0.1'].includes(web.hostname) ||
    web.username || web.password || web.pathname !== '/' || web.search || web.hash) {
  throw new Error('Local synthetic HTTP origin required')
}
if (!process.env.GISTAR_DEMO_PASSWORD) throw new Error('Set the synthetic demo password')

const { newBrowser, check, errors, finish, sleep } = await import('./cdp.mjs')
const accountName = 'Selección IA (demo)'
const consoleScope = 'document.querySelector(\'section[aria-label="Invitaciones de personal"]\')'

function requireCheck(label, result) {
  check(label, Boolean(result))
  if (!result) throw new Error(label)
}

async function openStaff(email, observe = false) {
  const page = await newBrowser()
  if (observe) await page.initScript(`(() => {
    const fetch = window.fetch.bind(window)
    window.staffQueueReads = 0
    window.staffWrites = []
    window.staffDirectFetch = fetch
    window.fetch = async (input, init) => {
      const path = new URL(typeof input === 'string' ? input : input.url, location.href).pathname
      const method = init?.method ?? input.method ?? 'GET'
      if (method === 'GET' && path === '/api/v1/staff/access-requests') window.staffQueueReads++
      const result = await fetch(input, init)
      if (method === 'POST' && path.startsWith('/api/v1/staff/invitations') && result.ok) {
        await new Promise(release => window.staffWrites.push({ path, release }))
      }
      return result
    }
  })()`)
  await page.goto(web.href)
  requireCheck('Staff sign-in form is ready', await page.waitText('Iniciar sesión'))
  await page.login(email)
  requireCheck('Personal action is available', await page.waitText('Personal'))
  requireCheck('Internal account opens Personal', await page.click('Personal'))
  return page
}

async function holdAndRelease(page, index) {
  for (let i = 0; i < 50; i++) {
    if (await page.ev(`window.staffWrites.length === ${index + 1}`)) break
    await sleep(100)
  }
  requireCheck('The server committed the invitation write before the response was released',
    await page.ev(`window.staffWrites.length === ${index + 1}`))
  const dialog = "document.querySelector('[role=dialog]')"
  await page.ev(`(() => {
    const dialog = ${dialog}
    dialog.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))
    dialog.querySelector('[aria-label="Cerrar"]').click()
    dialog.parentElement.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }))
    document.querySelector('nav[aria-label="Navegación principal"] button').click()
  })()`)
  requireCheck('Escape, close, backdrop and navigation keep the writing dialog open',
    await page.ev(`${dialog}?.querySelector('[aria-label="Cerrar"]').disabled`))
  await page.ev(`window.staffWrites[${index}].release()`)
}

async function waitForCode(page) {
  for (let i = 0; i < 30; i++) {
    const value = await page.ev(`${consoleScope}?.querySelector('code')?.textContent`)
    if (value) return value
    await sleep(200)
  }
  return null
}

async function submitCode(page, code) {
  return await page.set('#staff-invitation', code) && await page.click('Aceptar invitación')
}

try {
  const admin = await openStaff('admin@gistar.example', true)
  const recipient = await openStaff('seleccion.ia@gistar.example')
  requireCheck('Recipient sees acceptance and lacks administrative controls',
    await recipient.waitText('Aceptar invitación') && !(await recipient.text()).includes('Gestionar invitaciones'))
  requireCheck('Admin opens the invitation console', await admin.click('Gestionar invitaciones') && await admin.waitText(accountName))
  const accountId = await admin.ev(`[...document.querySelector('#staff-invitation-account').options].find(option => option.textContent.includes(${JSON.stringify(accountName)}))?.value`)
  requireCheck('Admin issues a code for the synthetic internal account',
    await admin.set('#staff-invitation-account', accountId) && await admin.click('Emitir código', consoleScope))
  await holdAndRelease(admin, 0)
  const firstCode = await waitForCode(admin)
  requireCheck('One-time code appears on its issuance receipt', firstCode)
  requireCheck('Admin rotates the code', await admin.waitText('Renovar código') && await admin.click('Renovar código', consoleScope))
  await holdAndRelease(admin, 1)
  const secondCode = await waitForCode(admin)
  requireCheck('Renewal returns a different code', secondCode && secondCode !== firstCode)
  requireCheck('Recipient cannot use the replaced code',
    await submitCode(recipient, firstCode) && await recipient.waitText('La invitación no está disponible'))

  await admin.ev('window.confirm = () => true')
  requireCheck('Admin revokes the pending code', await admin.click('Revocar código', consoleScope))
  await holdAndRelease(admin, 2)
  requireCheck('Revocation result appears after delivery', await admin.waitText('Invitación revocada.'))
  requireCheck('Dismissed receipt is absent from the browser view',
    await admin.ev(`!${consoleScope}.querySelector('code')`))
  requireCheck('Recipient cannot use the revoked code',
    await submitCode(recipient, secondCode) && await recipient.waitText('La invitación no está disponible'))

  requireCheck('Admin renews after revocation', await admin.waitText('Renovar código') && await admin.click('Renovar código', consoleScope))
  await holdAndRelease(admin, 3)
  const thirdCode = await waitForCode(admin)
  requireCheck('Recipient activates the staff profile', thirdCode && await submitCode(recipient, thirdCode) &&
    await recipient.waitText('Invitación aceptada.'))
  requireCheck('Admin initially read the queue once', await admin.ev('window.staffQueueReads === 1'))
  requireCheck('The staff member files a scoped teaching request',
    await recipient.set('#staff-scope-id', 'COH-IA') &&
    await recipient.click('Enviar solicitud de acceso') &&
    await recipient.waitText('Solicitud registrada y pendiente de revisión.'))
  await admin.click('Actualizar personal')
  requireCheck('The queue refresh shows the full accepted profile identifier',
    await admin.waitText('Aprobar solicitud') && await admin.ev(`[...document.querySelectorAll('li')].some(item =>
      item.textContent.includes(${JSON.stringify(accountName)}) &&
      /Ficha: [0-9a-f-]{36}/.test(item.textContent) && item.textContent.includes('COH-IA'))`))
  requireCheck('A refresh issues one queue read', await admin.ev('window.staffQueueReads === 2'))
  await admin.ev('window.confirm = text => { window.reviewConfirmation = text; return false }')
  await admin.click('Aprobar solicitud')
  requireCheck('The destructive decision requires confirmation naming requester, role and scope',
    await admin.ev(`window.reviewConfirmation.includes(${JSON.stringify(accountName)}) &&
      window.reviewConfirmation.includes('Ficha:') && window.reviewConfirmation.includes('COH-IA') &&
      document.body.innerText.includes('Aprobar solicitud') && window.staffQueueReads === 2`))

  const api = new URL('/api/v1/staff/access-requests', process.env.GISTAR_API ?? 'http://localhost:8000')
  requireCheck('A parallel administrative update makes the visible row stale', await admin.ev(`(async () => {
    const headers = { Authorization: 'Bearer ' + sessionStorage.getItem('gistar-api-token'), 'Content-Type': 'application/json' }
    const base = ${JSON.stringify(api.href)}
    const queue = await window.staffDirectFetch(base + '?pending_only=true', { headers }).then(r => r.json())
    const request = queue.items.find(item => item.scope_id === 'COH-IA')
    return (await window.staffDirectFetch(base + '/' + request.id + '/review', {
      method: 'POST', headers, body: JSON.stringify({ approved: true })
    })).ok
  })()`))
  await admin.ev('window.confirm = () => true')
  await admin.click('Aprobar solicitud')
  requireCheck('A conflict refreshes the stale row and removes review actions',
    await admin.waitText('No hay solicitudes en esta página.') &&
    await admin.ev('window.staffQueueReads === 3'))
  await admin.set('#staff-queue-state', 'approved')
  requireCheck('The separate application preview opens',
    await admin.waitText('Previsualizar aplicación') && await admin.click('Previsualizar aplicación') &&
    await admin.waitText('Confirmar y aplicar permiso'))
  requireCheck('Explicitly applying creates the scoped assignment',
    await admin.click('Confirmar y aplicar permiso') && await admin.waitText('Aplicación del permiso registrada.'))
  await admin.set('#staff-queue-state', 'all')
  requireCheck('The applied assignment can be inspected and revoked',
    await admin.waitText('Consultar aplicación') && await admin.click('Consultar aplicación') &&
    await admin.waitText('Revocar permiso') && await admin.click('Revocar permiso') &&
    await admin.waitText('Revocación registrada.'))
  requireCheck('The revoked assignment remains visible in the history',
    await admin.waitText('Consultar aplicación') && await admin.click('Consultar aplicación') &&
    await admin.waitText('La asignación está revocada.'))
  requireCheck('No uncaught browser errors', errors.length === 0)
} catch (error) {
  check('Staff invitation console journey', false, error.message)
} finally {
  finish()
}
