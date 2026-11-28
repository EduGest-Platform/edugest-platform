import { sleep } from './cdp.mjs'

export async function interceptWrites(page, pathnamePattern) {
  await page.initScript(`(() => {
    const fetch = window.fetch.bind(window)
    const matches = new RegExp(${JSON.stringify(pathnamePattern)})
    window.delayedWrites = []
    window.fetch = async (input, init) => {
      const path = new URL(input.url ?? input, location.href).pathname
      if (!['POST', 'PUT'].includes(init?.method ?? input.method) || !matches.test(path)) return fetch(input, init)
      const response = await fetch(input, init)
      await new Promise(release => window.delayedWrites.push({ release, ok: response.ok, path }))
      if (window.dropNextWrite) {
        window.dropNextWrite = false
        throw new TypeError('Synthetic response dropped after commit')
      }
      return response
    }
  })()`)
}

export async function waitForWrite(page, index) {
  for (let i = 0; i < 50; i++) {
    const committed = await page.ev(`window.delayedWrites[${index}]?.ok`)
    if (committed !== undefined) return committed
    await sleep(100)
  }
  return false
}

export async function tryDismiss(page, cohortSelector) {
  return page.ev(`(() => {
    const dialog = document.querySelector('[role=dialog]')
    if (!dialog) return false
    const close = dialog.querySelector('[aria-label="Cerrar"]')
    const cohort = document.querySelector(${JSON.stringify(cohortSelector)})
    window.confirm = () => true
    dialog.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))
    close.click()
    dialog.parentElement.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }))
    document.querySelector('nav[aria-label="Navegación principal"] button').click()
    return close.disabled && cohort.disabled && dialog.isConnected
  })()`)
}
