/** KAN-281: change appearance before login and preserve it across the session boundary. */
import { check, errors, finish, newBrowser } from './cdp.mjs'

const web = new URL(process.env.WEB_URL ?? 'http://localhost:8443/')
const password = process.env.GISTAR_DEMO_PASSWORD
if (web.protocol !== 'http:' || !['localhost', '127.0.0.1'].includes(web.hostname) ||
    web.username || web.password || web.pathname !== '/' || web.search || web.hash || !password) {
  throw new Error('Use a local synthetic web service and the demo password')
}
const page = await newBrowser()
function requireCheck(label, ok) {
  check(label, Boolean(ok))
  if (!ok) throw new Error(label)
}

try {
  await page.goto(web.href)
  requireCheck('The public login exposes appearance preferences', await page.waitText('Iniciar sesión') &&
    await page.click('EN') && await page.waitText('Demo account') && await page.waitText('Password'))
  const nightAlreadyActive = await page.ev("document.documentElement.dataset.theme === 'dark'")
  requireCheck('The login applies the selected dark theme',
    (nightAlreadyActive || await page.click('Night mode')) &&
    await page.ev("document.documentElement.dataset.theme === 'dark'"))
  await page.goto(web.href)
  requireCheck('English and dark mode persist before sign-in', await page.waitText('Demo account') &&
    await page.ev(`(() => {
      const field = document.getElementById('lg-pass')
      return document.documentElement.lang === 'es' && document.documentElement.dataset.theme === 'dark' &&
        field?.closest('[lang]')?.lang === 'en' && !!document.querySelector('nav[aria-label="Public access"]')
    })()`))
  requireCheck('Other public pages retain their Spanish fallback',
    await page.click('Browse courses', "document.querySelector('nav[aria-label=\"Public access\"]')") &&
    await page.ev(`(() => {
      const main = document.querySelector('main')
      return document.documentElement.lang === 'es' && !main.hasAttribute('lang') &&
        !document.getElementById('lg-pass')
    })()`))
  requireCheck('The translated form submits with unchanged synthetic credentials',
    await page.click('Sign in', "document.querySelector('nav[aria-label=\"Public access\"]')") &&
    await page.set('#lg-email', 'docente@gistar.example') && await page.set('#lg-pass', password) &&
    await page.click('Sign in', 'document.querySelector("form")'))
  requireCheck('The authenticated layout inherits both preferences', await page.waitText('Supporting every learning journey') &&
    await page.ev(`document.documentElement.dataset.theme === 'dark' &&
      !!document.querySelector('nav[aria-label="Main navigation"]')`))
  await page.ev("document.querySelector('[aria-label=\"Sign out\"]').click()")
  requireCheck('Signing out preserves language and theme', await page.waitText('Demo account') &&
    await page.ev("document.documentElement.dataset.theme === 'dark'"))
  requireCheck('No uncaught browser errors', errors.length === 0)
} catch (error) {
  check('Public sign-in appearance', false, error.message)
} finally {
  finish()
}
