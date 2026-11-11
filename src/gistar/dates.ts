/** Date helpers working on wall-clock strings (YYYY-MM-DD / YYYY-MM-DDTHH:mm, Europe/Madrid). No TZ conversions. */
const utc = (d: string) => new Date(d.slice(0, 10) + 'T00:00:00Z')

export const dayOf = (dt: string) => dt.slice(0, 10)
export const timeOf = (dt: string) => dt.slice(11, 16)

export function addDays(d: string, n: number) {
  const x = utc(d)
  x.setUTCDate(x.getUTCDate() + n)
  return x.toISOString().slice(0, 10)
}
/** 0 = lunes … 6 = domingo */
export const weekday = (d: string) => (utc(d).getUTCDay() + 6) % 7
export const weekStart = (d: string) => addDays(d, -weekday(d))
export const monthStart = (d: string) => d.slice(0, 8) + '01'
export function addMonths(d: string, n: number) {
  const x = utc(monthStart(d))
  x.setUTCMonth(x.getUTCMonth() + n)
  return x.toISOString().slice(0, 10)
}
export const daysBetween = (a: string, b: string) => Math.round((utc(b).getTime() - utc(a).getTime()) / 86400000)

const fmt = (opts: Intl.DateTimeFormatOptions) => new Intl.DateTimeFormat('es-ES', { timeZone: 'UTC', ...opts })
const fShort = fmt({ weekday: 'short', day: 'numeric', month: 'short' })
const fDay = fmt({ day: 'numeric', month: 'short' })
const fLong = fmt({ weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })
const fMonth = fmt({ month: 'long', year: 'numeric' })

export const fmtShort = (d: string) => fShort.format(utc(d))
export const fmtDay = (d: string) => fDay.format(utc(d))
export const fmtLong = (d: string) => fLong.format(utc(d))
export const fmtMonth = (d: string) => {
  const t = fMonth.format(utc(d))
  return t.charAt(0).toUpperCase() + t.slice(1)
}
export const fmtDateTime = (dt: string) => `${fmtShort(dt)} · ${timeOf(dt)}`
