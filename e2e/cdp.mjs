/** Minimal Chrome DevTools Protocol harness (no dependencies). To be replaced by Playwright in F5. */
import { spawn } from 'node:child_process'

export const PASSWORD = process.env.GISTAR_DEMO_PASSWORD ?? 'gistar-demo-2026'
const CHROME = process.env.CHROME_BIN ?? 'chromium'
export const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
export const results = []
export const check = (name, ok, extra = '') => {
  results.push({ name, ok })
  console.log(`${ok ? 'PASS' : 'FAIL'} · ${name}${extra ? ' — ' + extra : ''}`)
}

const PORT = 9300 + Math.floor(Math.random() * 90)
const chrome = spawn(CHROME, ['--headless=new', '--no-sandbox', '--disable-gpu', `--remote-debugging-port=${PORT}`, `--user-data-dir=/tmp/e2e-${Date.now()}`, 'about:blank'], { stdio: 'ignore' })
let ver
for (let i = 0; i < 40 && !ver; i++) {
  try {
    ver = await (await fetch(`http://127.0.0.1:${PORT}/json/version`)).json()
  } catch {
    await sleep(250)
  }
}
const ws = new WebSocket(ver.webSocketDebuggerUrl)
await new Promise((r) => ws.addEventListener('open', r))
let seq = 0
const pending = new Map()
export const errors = []
ws.addEventListener('message', (m) => {
  const msg = JSON.parse(m.data)
  if (msg.id && pending.has(msg.id)) {
    pending.get(msg.id)(msg)
    pending.delete(msg.id)
  }
  if (msg.method === 'Runtime.exceptionThrown') errors.push(msg.params.exceptionDetails.exception?.description ?? msg.params.exceptionDetails.text)
})
const send = (method, params = {}, sessionId) =>
  new Promise((r) => {
    const id = ++seq
    pending.set(id, r)
    ws.send(JSON.stringify({ id, method, params, sessionId }))
  })

/** Isolated browser context = a second browser with its own storage. */
export async function newBrowser() {
  const { result: ctx } = await send('Target.createBrowserContext')
  const { result: t } = await send('Target.createTarget', { url: 'about:blank', browserContextId: ctx.browserContextId })
  const { result: a } = await send('Target.attachToTarget', { targetId: t.targetId, flatten: true })
  const s = a.sessionId
  await send('Runtime.enable', {}, s)
  await send('Page.enable', {}, s)
  const ev = async (expr) => (await send('Runtime.evaluate', { expression: expr, awaitPromise: true, returnByValue: true }, s)).result?.result?.value
  const page = {
    ev,
    shot: async (file, width = 1280, height = 900) => {
      await send('Emulation.setDeviceMetricsOverride', { width, height, deviceScaleFactor: 1, mobile: false }, s)
      await sleep(300)
      const { result } = await send('Page.captureScreenshot', { format: 'png' }, s)
      ;(await import('node:fs')).writeFileSync(file, Buffer.from(result.data, 'base64'))
    },
    goto: async (url) => {
      await send('Page.navigate', { url }, s)
      await sleep(1500)
    },
    text: () => ev('document.body.innerText'),
    waitText: async (t, ms = 6000) => {
      for (let i = 0; i < ms / 200; i++) {
        if ((await ev('document.body.innerText'))?.includes(t)) return true
        await sleep(200)
      }
      return false
    },
    set: (sel, v) =>
      ev(`(() => { const el = document.querySelector(${JSON.stringify(sel)}); if (!el) return false;
        const proto = el.tagName === 'SELECT' ? HTMLSelectElement.prototype : el.tagName === 'TEXTAREA' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
        Object.getOwnPropertyDescriptor(proto, 'value').set.call(el, ${JSON.stringify(v)});
        el.dispatchEvent(new Event(el.tagName === 'SELECT' ? 'change' : 'input', { bubbles: true })); return true })()`),
    click: (text, scope = 'document') =>
      ev(`(() => { const b = [...${scope}.querySelectorAll('button')].find(b => b.textContent.trim().startsWith(${JSON.stringify(text)}) && !b.disabled); if (!b) return false; b.click(); return true })()`),
    nav: (label) => ev(`(() => { const b = [...document.querySelectorAll('nav[aria-label="Navegación principal"] button')].find(b => b.textContent.includes(${JSON.stringify(label)})); if (!b) return false; b.click(); return true })()`),
    rows: () => ev(`document.querySelectorAll('main tbody tr').length`),
    login: async (email) => {
      await page.set('#lg-email', email)
      await page.set('#lg-pass', PASSWORD)
      await page.click('Entrar')
      await sleep(900)
    },
  }
  return page
}


export function finish() {
  const failed = results.filter((r) => !r.ok).length
  console.log(`\n${results.length - failed}/${results.length} comprobaciones superadas`)
  ws.close()
  chrome.kill()
  process.exit(failed ? 1 : 0)
}
