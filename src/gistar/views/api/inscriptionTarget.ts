/** A catalogue handoff pins its call; a withdrawn offer must never fall back to another one. */
export function inscriptionTarget(calls: readonly { id: string }[], selectedId: string, pinnedId?: string) {
  const id = pinnedId ?? (selectedId || calls[0]?.id || '')
  return { id, available: calls.some((call) => call.id === id) }
}
