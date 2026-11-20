// WCAG contrast ratio between two colours.
// Usage: node contrast.mjs '#4f38e0' '#15295a'
// Text needs 4.5:1 (large text 3:1). Focus rings and icons need 3:1.

const [a, b] = process.argv.slice(2)
if (!a || !b) {
  console.error("Usage: node contrast.mjs '#rrggbb' '#rrggbb'")
  process.exit(1)
}

function luminance(hex) {
  const clean = hex.replace('#', '')
  const channels = [0, 2, 4].map((i) => parseInt(clean.slice(i, i + 2), 16) / 255)
  const linear = channels.map((c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4))
  return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]
}

const [light, dark] = [luminance(a), luminance(b)].sort((x, y) => y - x)
const ratio = (light + 0.05) / (dark + 0.05)
const verdict = ratio >= 4.5 ? 'PASS text and focus' : ratio >= 3 ? 'PASS large text and focus only' : 'FAIL'
console.log(`${a} on ${b}: ${ratio.toFixed(2)}:1 · ${verdict}`)
