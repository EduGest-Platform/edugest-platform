/**
 * When the API answers with an error, this file turns it into a short, friendly message in Spanish.
 * Each message says what happened and what to do next.
 * This way people never see technical codes like "HTTP 403".
 */

export type ApiProblemKind =
  | 'unauthorized'
  | 'forbidden'
  | 'not_found'
  | 'conflict'
  | 'invalid'
  | 'rate_limited'
  | 'server'
  | 'network'
  | 'unknown'

export interface ApiProblem {
  kind: ApiProblemKind
  /** What happened, in one short sentence. */
  title: string
  /** What the person can do now. */
  hint: string
}

const PROBLEMS: Record<ApiProblemKind, Omit<ApiProblem, 'kind'>> = {
  unauthorized: { title: 'Tu sesión ha caducado o se ha cerrado.', hint: 'Vuelve a iniciar sesión para continuar.' },
  forbidden: { title: 'No tienes permiso para ver esta información.', hint: 'Si crees que deberías tener acceso, pídeselo a coordinación.' },
  not_found: { title: 'No hemos encontrado lo que buscas.', hint: 'Puede que se haya borrado o que el enlace no sea correcto.' },
  conflict: { title: 'No se ha podido guardar porque choca con datos que ya existen.', hint: 'Revisa los datos. Si otra persona los ha cambiado, recarga la página.' },
  invalid: { title: 'Hay datos que no son válidos.', hint: 'Revisa los campos marcados y vuelve a enviar.' },
  rate_limited: { title: 'Has hecho demasiadas peticiones seguidas.', hint: 'Espera un minuto y vuelve a intentarlo.' },
  server: { title: 'El servidor ha tenido un problema.', hint: 'Inténtalo de nuevo en unos minutos.' },
  network: { title: 'No se puede conectar con el servidor.', hint: 'Comprueba tu conexión e inténtalo de nuevo.' },
  unknown: { title: 'No se ha podido completar la operación.', hint: 'Inténtalo de nuevo.' },
}

export function problemKindFor(status: number | undefined): ApiProblemKind {
  if (status === undefined || status === 0) return 'network'
  if (status === 401) return 'unauthorized'
  if (status === 403) return 'forbidden'
  if (status === 404) return 'not_found'
  if (status === 409) return 'conflict'
  if (status === 400 || status === 422) return 'invalid'
  if (status === 429) return 'rate_limited'
  if (status >= 500) return 'server'
  return 'unknown'
}

/** Reads the error text sent by the API (`detail`). It can be a sentence or a list of wrong fields. Returns null if there is none. */
export function detailText(body: unknown): string | null {
  const detail = (body as { detail?: unknown } | null | undefined)?.detail
  if (typeof detail === 'string' && detail.trim()) return detail
  if (Array.isArray(detail) && detail.length) {
    return detail
      .map((d: { loc?: (string | number)[]; msg?: string }) => `${d.loc?.slice(-1)[0] ?? 'campo'}: ${d.msg ?? 'no válido'}`)
      .join(' · ')
  }
  return null
}

/**
 * Builds the message for one failed request.
 * For wrong data (400/422) and conflicts (409) we keep the API text, because it says which field is wrong.
 * For 401 and 403 we always use our own text, so we never show internal details.
 */
export function describeApiError(status: number | undefined, body?: unknown): ApiProblem {
  const kind = problemKindFor(status)
  const base = { kind, ...PROBLEMS[kind] }
  const serverText = kind === 'invalid' || kind === 'conflict' ? detailText(body) : null
  return serverText ? { ...base, hint: serverText } : base
}

/** The whole message in one line, for small pop-up messages. */
export function problemText(problem: ApiProblem): string {
  return `${problem.title} ${problem.hint}`
}
