/**
 * E2E · regresión del modo local (sin VITE_GISTAR_API_URL), el que muestra la preview de Figma Make.
 * Recorre todas las vistas de los siete perfiles, migra un estado v1 y comprueba que no hay errores.
 * Uso: WEB_URL=http://localhost:3000/ node e2e/local-mode.mjs
 */
import { readFileSync } from 'node:fs'
import { check, errors, finish, newBrowser, sleep } from './cdp.mjs'

const WEB = process.env.WEB_URL ?? 'http://localhost:3000/'
const seed = readFileSync(new URL('../src/gistar/seed.json', import.meta.url), 'utf8')
const P = await newBrowser()
await P.goto(WEB)
await P.ev(`localStorage.clear(); localStorage.setItem('gistar-demo-v1', ${JSON.stringify(seed)}); true`)
await P.goto(WEB)
check('Migración v1 → v2 conserva la clave v1', (await P.ev(`JSON.parse(localStorage.getItem('gistar-demo-v2') || '{}').schema_version === 2 && !!localStorage.getItem('gistar-demo-v1')`)) === true)
check('Selector «Ver como» disponible en modo local', (await P.ev(`document.querySelectorAll('#role option').length`)) === 7)

let views = 0
for (const role of ['admin', 'docente', 'coder', 'aspirante', 'fundacion', 'seleccion', 'coordinacion']) {
  await P.set('#role', role)
  await sleep(300)
  const n = await P.ev(`document.querySelectorAll('nav[aria-label="Navegación principal"] button').length`)
  for (let i = 0; i < n; i++) {
    const before = errors.length
    const label = await P.ev(`(() => { const b = document.querySelectorAll('nav[aria-label="Navegación principal"] button')[${i}]; b.click(); return b.textContent })()`)
    await sleep(350)
    const h1 = await P.ev(`document.querySelector('main h1')?.textContent ?? ''`)
    views++
    if (!h1 || errors.length > before) check(`${role} › ${label}`, false, errors.slice(before).join(' | '))
  }
}
check(`Todas las vistas renderizan (${views} combinaciones rol×vista)`, views >= 36 && errors.length === 0)
check('Modo local no muestra pantalla de acceso ni avisos de servidor', !(await P.text()).includes('Iniciar sesión') && !(await P.text()).includes('Datos del servidor'))
finish()
