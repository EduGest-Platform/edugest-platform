/** KAN-221: run the release walkthrough and failure cases within the demo slot. */
import { spawnSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'

function loopbackOrigin(raw) {
  const url = new URL(raw)
  if (url.protocol !== 'http:' || !['127.0.0.1', 'localhost'].includes(url.hostname) ||
      url.username || url.password || url.pathname !== '/' || url.search || url.hash) {
    throw new Error('The rehearsal requires local synthetic HTTP services.')
  }
  return url
}

const web = loopbackOrigin(process.env.WEB_URL ?? 'http://localhost:8443/')
const api = loopbackOrigin(process.env.GISTAR_API ?? 'http://localhost:8000/')
if (process.env.GISTAR_E2E_FIXTURE !== 'disposable-synthetic' || !process.env.GISTAR_DEMO_PASSWORD) {
  throw new Error('Set the disposable fixture marker and the synthetic demo password.')
}
const stages = [
  { label: 'Registration, unavailable call list and retry', script: 'f1-registration.mjs', fixture: 'demo-rehearsal-intake' },
  { label: 'Human quorum, out-of-scope denial and attendance', script: 'f2-admission-enrollment.mjs', fixture: 'demo-rehearsal-f2' },
  { label: 'Repeat HTTP flow without duplicate enrollment', script: 'f2-admission-enrollment.mjs', fixture: 'demo-rehearsal-f2' },
  { label: 'Cited answer, connection failure and cancellation', script: 'assistant-keyboard.mjs' },
]

const start = performance.now()
const durationMs = 15 * 60 * 1000
const completed = []
function report() {
  console.log('\nStage timing (seconds):')
  for (const item of completed) console.log(`${item.label}: ${item.seconds.toFixed(2)} s — ${item.status}`)
  console.log(`Remaining budget: ${Math.max(0, (durationMs - (performance.now() - start)) / 1000).toFixed(2)} s`)
}
for (const stage of stages) {
  const remaining = Math.floor(durationMs - (performance.now() - start))
  if (remaining <= 0) {
    console.error('Demo slot expired before ' + stage.label)
    report()
    process.exit(1)
  }
  console.log('\n' + stage.label)
  const stageStart = performance.now()
  const result = spawnSync(process.execPath, [fileURLToPath(new URL(stage.script, import.meta.url))], {
    env: {
      ...process.env, WEB_URL: web.href, GISTAR_API: api.origin,
      ...(stage.fixture ? { E2E_FIXTURE_ID: stage.fixture } : {}),
    },
    stdio: 'inherit',
    timeout: remaining,
  })
  const failed = Boolean(result.error || result.status !== 0)
  completed.push({ label: stage.label, seconds: (performance.now() - stageStart) / 1000, status: failed ? 'FAILED' : 'PASSED' })
  if (failed) {
    console.error(result.error?.code === 'ETIMEDOUT'
      ? 'The demo slot expired during this step.'
      : 'Rehearsal stopped at this step. Read the failed check above.')
    report()
    process.exit(1)
  }
}
report()
console.log(`\nRehearsal passed in ${Math.ceil((performance.now() - start) / 1000)} seconds (900-second slot).`)
