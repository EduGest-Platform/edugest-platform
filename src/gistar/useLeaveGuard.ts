import { useEffect, useRef } from 'react'
import { useGistar } from './store'

export function useLeaveGuard(blocked: boolean, message?: string) {
  const { registerLeaveGuard } = useGistar()
  const state = useRef({ blocked, message })
  state.current = { blocked, message }

  useEffect(() => registerLeaveGuard(() => {
    const current = state.current
    return !current.blocked && (!current.message || window.confirm(current.message))
  }), [registerLeaveGuard])

  useEffect(() => {
    if (!blocked && !message) return
    function confirmUnload(event: BeforeUnloadEvent) {
      event.preventDefault()
      event.returnValue = ''
    }
    window.addEventListener('beforeunload', confirmUnload)
    return () => window.removeEventListener('beforeunload', confirmUnload)
  }, [blocked, message])
}
