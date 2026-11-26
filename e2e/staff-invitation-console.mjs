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

async function openStaff(email) {
  const page = await newBrowser()
  await page.goto(web.href)
  await page.login(email)
  requireCheck('Internal account opens Personal', await page.click('Personal'))
  return page
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
  const admin = await openStaff('admin@gistar.example')
  const recipient = await openStaff('seleccion.ia@gistar.example')
  requireCheck('Recipient sees acceptance and lacks administrative controls',
    await recipient.waitText('Aceptar invitación') && !(await recipient.text()).includes('Gestionar invitaciones'))
  requireCheck('Admin opens the invitation console', await admin.click('Gestionar invitaciones') && await admin.waitText(accountName))
  const accountId = await admin.ev(`[...document.querySelector('#staff-invitation-account').options].find(option => option.textContent.includes(${JSON.stringify(accountName)}))?.value`)
  requireCheck('Admin issues a code for the synthetic internal account',
    await admin.set('#staff-invitation-account', accountId) && await admin.click('Emitir código', consoleScope))
  const firstCode = await waitForCode(admin)
  requireCheck('One-time code appears on its issuance receipt', firstCode)
  requireCheck('Admin rotates the code', await admin.waitText('Renovar código') && await admin.click('Renovar código', consoleScope))
  const secondCode = await waitForCode(admin)
  requireCheck('Renewal returns a different code', secondCode && secondCode !== firstCode)
  requireCheck('Recipient cannot use the replaced code',
    await submitCode(recipient, firstCode) && await recipient.waitText('La invitación no está disponible'))

  await admin.ev('window.confirm = () => true')
  requireCheck('Admin revokes the pending code', await admin.click('Revocar código', consoleScope)
    && await admin.waitText('Invitación revocada.'))
  requireCheck('Dismissed receipt is absent from the browser view',
    await admin.ev(`!${consoleScope}.querySelector('code')`))
  requireCheck('Recipient cannot use the revoked code',
    await submitCode(recipient, secondCode) && await recipient.waitText('La invitación no está disponible'))

  requireCheck('Admin renews after revocation', await admin.waitText('Renovar código') && await admin.click('Renovar código', consoleScope))
  const thirdCode = await waitForCode(admin)
  requireCheck('Recipient activates the staff profile', thirdCode && await submitCode(recipient, thirdCode) &&
    await recipient.waitText('Invitación aceptada.'))
  requireCheck('No uncaught browser errors', errors.length === 0)
} catch (error) {
  check('Staff invitation console journey', false, error.message)
} finally {
  finish()
}
