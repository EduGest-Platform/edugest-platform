import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import type { Role } from '../../gistar/types'
import { api, errorMessage, setUnauthorizedHandler, tokenStore, type Schemas } from './client'
import { API_MODE } from './config'

export type Me = Schemas['MeOut']

/** API roles → prototype views. Aspirant and coder are Person states, not roles. */
const ROLE_TO_UI: Record<string, Role> = {
  admin: 'admin',
  coordinacion: 'coordinacion',
  captacion: 'fundacion',
  seleccion: 'seleccion',
  docente: 'docente',
}
const PRIORITY: Role[] = ['admin', 'coordinacion', 'fundacion', 'seleccion', 'docente', 'coder', 'aspirante']

export function uiRolesFor(me: Me): Role[] {
  const set = new Set<Role>(me.roles.map((r) => ROLE_TO_UI[r.role]).filter(Boolean))
  if (me.enrollments.length) set.add('coder')
  if (!set.size) set.add('aspirante')
  return PRIORITY.filter((r) => set.has(r))
}

interface SessionCtx {
  enabled: boolean
  me: Me | null
  loading: boolean
  apiDown: boolean
  login: (email: string, password: string) => Promise<string | null>
  logout: () => Promise<void>
  refresh: () => Promise<void>
}

const Ctx = createContext<SessionCtx>({
  enabled: false,
  me: null,
  loading: false,
  apiDown: false,
  login: async () => null,
  logout: async () => undefined,
  refresh: async () => undefined,
})

export function ApiSessionProvider({ children }: { children: ReactNode }) {
  const [me, setMe] = useState<Me | null>(null)
  const [loading, setLoading] = useState(API_MODE)
  const [apiDown, setApiDown] = useState(false)

  const refresh = useCallback(async () => {
    if (!API_MODE) return
    if (!tokenStore.get()) {
      setMe(null)
      return
    }
    try {
      const { data } = await api.GET('/api/v1/auth/me')
      setMe(data ?? null)
      setApiDown(false)
    } catch {
      setApiDown(true)
    }
  }, [])

  useEffect(() => {
    if (!API_MODE) return
    setUnauthorizedHandler(() => {
      tokenStore.clear()
      setMe(null)
    })
    refresh().finally(() => setLoading(false))
    return () => setUnauthorizedHandler(null)
  }, [refresh])

  const login = useCallback(async (email: string, password: string) => {
    try {
      const { data, error } = await api.POST('/api/v1/auth/login', { body: { email, password } })
      if (error || !data) return errorMessage(error, 'Credenciales no válidas')
      tokenStore.set(data.access_token)
      setMe(data.me)
      setApiDown(false)
      return null
    } catch {
      setApiDown(true)
      return 'No se puede conectar con la API'
    }
  }, [])

  const logout = useCallback(async () => {
    try {
      await api.POST('/api/v1/auth/logout')
    } finally {
      tokenStore.clear()
      setMe(null)
    }
  }, [])

  const value = useMemo(() => ({ enabled: API_MODE, me, loading, apiDown, login, logout, refresh }), [me, loading, apiDown, login, logout, refresh])
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

export const useApiSession = () => useContext(Ctx)
