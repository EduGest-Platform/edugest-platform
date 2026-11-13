import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import seedJson from './seed.json'
import { canOpen } from './config'
import { migrate } from './migrate'
import { nominalCohorts } from './domain'
import type { GistarData, Role, View } from './types'

const STORAGE_KEY = 'gistar-demo-v2'
/** Previous schema key: read for migration, never deleted (user data is preserved). */
const LEGACY_KEY = 'gistar-demo-v1'
const buildSeed = () => migrate(structuredClone(seedJson))

function load(): { data: GistarData; migrated: boolean } {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) return { data: migrate(JSON.parse(raw)), migrated: false }
    const legacy = localStorage.getItem(LEGACY_KEY)
    if (legacy) {
      const data = migrate(JSON.parse(legacy))
      data.meta.migrado_desde = LEGACY_KEY
      return { data, migrated: true }
    }
  } catch {
    /* corrupt storage: fall back to seed */
  }
  return { data: buildSeed(), migrated: false }
}

interface Store {
  data: GistarData
  role: Role
  view: View
  setRole: (r: Role) => void
  navigate: (v: View) => void
  /** Mutates a draft copy, records the action in the audit log, persists and notifies. */
  update: (mutate: (draft: GistarData) => void, action: string, entity: string, detail?: string, toastMsg?: string) => void
  reset: () => void
  toast: (msg: string) => void
  toastMsg: string | null
  focusStudent: string
  setFocusStudent: (id: string) => void
  focusComp: string | null
  setFocusComp: (id: string | null) => void
  teacherCohort: string
  setTeacherCohort: (id: string) => void
}

const Ctx = createContext<Store | null>(null)

export function GistarProvider({ children }: { children: ReactNode }) {
  const [initial] = useState(load)
  const [data, setData] = useState<GistarData>(initial.data)
  const [role, setRoleState] = useState<Role>('docente')
  const [view, setView] = useState<View>('dashboard')
  const [toastMsg, setToastMsg] = useState<string | null>(null)
  const [focusStudent, setFocusStudent] = useState('E-001')
  const [focusComp, setFocusComp] = useState<string | null>(null)
  const [teacherCohort, setTeacherCohort] = useState(() => nominalCohorts(initial.data, 'docente')[0]?.id ?? 'COH-IA')
  const timer = useRef<number | undefined>(undefined)

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data))
  }, [data])

  const toast = useCallback((msg: string) => {
    setToastMsg(msg)
    window.clearTimeout(timer.current)
    timer.current = window.setTimeout(() => setToastMsg(null), 3100)
  }, [])

  useEffect(() => {
    if (initial.migrated) toast('Datos locales migrados al esquema v2 sin pérdida')
  }, [initial.migrated, toast])

  const setRole = useCallback((r: Role) => {
    setRoleState(r)
    setView('dashboard')
  }, [])

  const navigate = useCallback(
    (v: View) => {
      if (!canOpen(role, v)) return toast('Acceso no permitido para este rol')
      setView(v)
      window.scrollTo({ top: 0 })
    },
    [role, toast],
  )

  const update = useCallback<Store['update']>(
    (mutate, action, entity, detail = 'Operación simulada registrada', msg = 'Cambio guardado en la demo') => {
      setData((prev) => {
        const draft = structuredClone(prev)
        mutate(draft)
        draft.bitacora_demo.unshift({
          id: 'EV-' + Date.now() + Math.random().toString(36).slice(2, 5),
          fecha_simulada: draft.meta.fecha_simulada,
          actor_rol: role,
          entidad: entity,
          accion: action,
          detalle: detail,
        })
        return draft
      })
      toast(msg)
    },
    [role, toast],
  )

  const reset = useCallback(() => {
    if (!confirm('¿Restablecer todos los datos sintéticos al estado inicial?')) return
    localStorage.removeItem(STORAGE_KEY)
    const seed = buildSeed()
    setData(seed)
    setRoleState('docente')
    setView('dashboard')
    setTeacherCohort(nominalCohorts(seed, 'docente')[0]?.id ?? 'COH-IA')
    toast('Demo restablecida')
  }, [toast])

  const value = useMemo(
    () => ({ data, role, view, setRole, navigate, update, reset, toast, toastMsg, focusStudent, setFocusStudent, focusComp, setFocusComp, teacherCohort, setTeacherCohort }),
    [data, role, view, setRole, navigate, update, reset, toast, toastMsg, focusStudent, focusComp, teacherCohort],
  )
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

export function useGistar() {
  const ctx = useContext(Ctx)
  if (!ctx) throw new Error('useGistar must be used within GistarProvider')
  return ctx
}
