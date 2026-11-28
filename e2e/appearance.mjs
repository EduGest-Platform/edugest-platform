/** Check shared controls and language metadata in the local synthetic demo. */
import { check, errors, finish, newBrowser, sleep } from './cdp.mjs'

const web = process.env.WEB_URL ?? 'http://localhost:4173/'
const page = await newBrowser()
const buttons = {
  primary: 'main button.bg-action-primary',
  ghost: '[role=dialog] button.bg-action-quiet',
  success: '[role=dialog] button.bg-action-success:not(:disabled)',
  subtle: '[role=dialog] button.bg-transparent:not(:disabled)',
}
const ratio = (first, second) => {
  const light = color => color.match(/[\d.]+/g).slice(0, 3).map(x => Number(x) / 255)
    .map(x => x <= 0.04045 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4)
    .reduce((sum, channel, i) => sum + channel * [0.2126, 0.7152, 0.0722][i], 0)
  const levels = [light(first), light(second)].sort((a, b) => b - a)
  return (levels[0] + 0.05) / (levels[1] + 0.05)
}

async function measure(selector) {
  return page.ev(`(() => {
    const button = document.querySelector(${JSON.stringify(selector)})
    if (!button) return null
    const style = getComputedStyle(button)
    let surface = button
    while (surface && getComputedStyle(surface).backgroundColor === 'rgba(0, 0, 0, 0)') {
      surface = surface.parentElement
    }
    return { foreground: style.color, background: getComputedStyle(surface).backgroundColor,
      outline: style.outlineColor, visible: button.matches(':focus-visible') }
  })()`)
}

async function hoverButton(selector) {
  for (let attempt = 0; attempt < 6; attempt++) {
    const clearHover = await page.hover(selector)
    await sleep(250)
    if (await page.ev(`document.querySelector(${JSON.stringify(selector)})?.matches(':hover')`)) {
      return clearHover
    }
    await clearHover()
  }
  throw new Error(`Pointer could not reach ${selector}`)
}

async function verifyContrast(selector, label) {
  const colors = await measure(selector)
  const contrast = colors ? ratio(colors.foreground, colors.background) : 0
  check(label, contrast >= 4.5, colors
    ? `${colors.foreground} / ${colors.background} = ${contrast.toFixed(2)}:1` : 'button unavailable')
  return colors?.background
}

try {
  await page.initScript('window.confirm = () => true')
  await page.goto(web)
  if (!await page.waitText('Modo noche', 15000)) throw new Error('Appearance controls unavailable')
  if (await page.ev("document.documentElement.dataset.theme === 'dark'")) await page.click('Modo noche')
  for (const theme of ['light', 'dark']) {
    check(`${theme} theme active`, await page.ev(`document.documentElement.dataset.theme === '${theme}'`))
    if (!await page.nav('Rúbricas') || !await page.waitText('Nueva versión')) throw new Error('Rubric view unavailable')
    const primaryDefault = await verifyContrast(buttons.primary, `${theme} primary default`)
    const clearPrimaryHover = await hoverButton(buttons.primary)
    const primaryHover = await verifyContrast(buttons.primary, `${theme} primary hover`)
    check(`${theme} primary changes on hover`, primaryDefault !== primaryHover)
    await clearPrimaryHover()
    await sleep(250)
    if (!await page.click('Duplicar') || !await page.waitText('Guardar borrador')) throw new Error('Rubric form unavailable')
    for (const variant of ['ghost', 'success', 'subtle']) {
      const selector = buttons[variant]
      const defaultBackground = await verifyContrast(selector, `${theme} ${variant} default`)
      const clearHover = await hoverButton(selector)
      const hoverBackground = await verifyContrast(selector, `${theme} ${variant} hover`)
      check(`${theme} ${variant} changes on hover`, defaultBackground !== hoverBackground)
      await clearHover()
      await sleep(250)
    }
    await page.ev(`document.querySelector('[role=dialog] [aria-label="Cerrar"]').focus()`)
    await page.tab()
    await page.ev(`document.querySelector(${JSON.stringify(buttons.ghost)}).focus()`)
    const focused = await page.ev(`(() => {
      const element = document.activeElement
      return element.matches(':focus-visible') && getComputedStyle(element).outlineStyle === 'solid'
    })()`)
    check(`${theme} keyboard focus remains visible`, focused)
    check(`${theme} disabled control has distinct styling`, await page.ev(`(() => {
      const control = document.querySelector('[role=dialog] button:disabled')
      return control && getComputedStyle(control).opacity === '0.5' && getComputedStyle(control).cursor === 'not-allowed'
    })()`))
    if (process.env.APPEARANCE_SHOTS) await page.shot(`${process.env.APPEARANCE_SHOTS}/appearance-${theme}.png`)
    await page.ev(`document.querySelector('[role=dialog] [aria-label="Cerrar"]').click()`)
    if (theme === 'light') await page.click('Modo noche')
  }
  await page.click('EN')
  check('English chrome and Spanish screen carry their own language metadata', await page.ev(`(() => {
    const nav = document.querySelector('nav[aria-label="Main navigation"]')
    const heading = document.querySelector('main h1')
    return document.documentElement.lang === 'es' && nav?.lang === 'en' &&
      nav.textContent.includes('Rubrics') && heading?.closest('[lang]')?.lang === 'es' &&
      heading.textContent.includes('Rúbricas')
  })()`))
  await page.goto(web)
  check('Reload retains language and theme without changing the document language', await page.waitText('Night mode') && await page.ev(`(() => {
    const controls = document.querySelector('section[aria-label="Appearance preferences"]')
    return document.documentElement.lang === 'es' && document.documentElement.dataset.theme === 'dark' &&
      controls?.querySelector('button[lang=en]')?.getAttribute('aria-pressed') === 'true'
  })()`))
  await page.click('ES')
  check('Spanish chrome and Spanish screen restore matching language', await page.ev(`
    document.querySelector('nav[aria-label="Navegación principal"]')?.lang === 'es' &&
    document.documentElement.lang === 'es'`))
  if (!await page.set('#role', 'docente') || !await page.nav('Alumnado') ||
      !await page.ev("!!document.querySelector('main [role=progressbar] > span')")) {
    throw new Error('Teacher progress view unavailable')
  }
  for (const width of [1280, 390]) {
    for (const reduce of [false, true]) {
      await page.emulateMotion(width, 844, reduce)
      check(`Motion preference at ${width}px (${reduce ? 'reduced' : 'normal'})`, await page.ev(`(() => {
        const reduce = ${reduce}
        const main = document.querySelector('main')
        const nav = document.querySelector('nav[aria-label="Navegación principal"] button')
        const button = Array.from(main.querySelectorAll('button')).find(el => el.classList.contains('motion-safe:duration-200'))
        const progress = main.querySelector('[role=progressbar] > span')
        if (![nav, button, progress].every(Boolean) || innerWidth !== ${width}) return false
        const hasTransition = el => getComputedStyle(el).transitionDuration.split(',').some(value => parseFloat(value) > 0)
        return matchMedia('(prefers-reduced-motion: reduce)').matches === reduce &&
          (getComputedStyle(main).animationName !== 'none') === !reduce &&
          [nav, button, progress].every(el => hasTransition(el) === !reduce)
      })()`))
    }
  }
  check('No uncaught browser errors', errors.length === 0)
} catch (error) {
  check('Appearance journey', false, error.message)
} finally {
  finish()
}
