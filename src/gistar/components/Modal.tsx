import { useEffect, useRef, type KeyboardEvent, type ReactNode } from 'react'
import { createPortal } from 'react-dom'
import { X } from 'lucide-react'

const FOCUSABLE = 'a[href],button:not([disabled]),textarea:not([disabled]),input:not([disabled]),select:not([disabled]),[tabindex]:not([tabindex="-1"])'

/**
 * Wide centred dialog (near full-screen on mobile) with internal scroll, sticky footer,
 * Esc / close button, focus trap, focus return and an unsaved-changes guard.
 */
export function Modal({
  open,
  onClose,
  title,
  subtitle,
  children,
  footer,
  dirty = false,
  size = 'xl',
}: {
  open: boolean
  onClose: () => void
  title: ReactNode
  subtitle?: ReactNode
  children: ReactNode
  footer?: ReactNode
  dirty?: boolean
  size?: 'md' | 'lg' | 'xl'
}) {
  const ref = useRef<HTMLDivElement>(null)
  const dirtyRef = useRef(dirty)
  dirtyRef.current = dirty
  const closeRef = useRef(onClose)
  closeRef.current = onClose

  const requestClose = () => {
    if (dirtyRef.current && !confirm('Hay cambios sin guardar. ¿Quieres descartarlos?')) return
    closeRef.current()
  }

  useEffect(() => {
    if (!open) return
    const prev = document.activeElement as HTMLElement | null
    const el = ref.current
    const first = el?.querySelector<HTMLElement>('[data-autofocus]') ?? el?.querySelector<HTMLElement>(FOCUSABLE)
    ;(first ?? el)?.focus()
    const overflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = overflow
      prev?.focus?.()
    }
  }, [open])

  if (!open) return null

  const onKeyDown = (e: KeyboardEvent) => {
    if (e.key === 'Escape') {
      e.stopPropagation()
      requestClose()
    }
    if (e.key !== 'Tab' || !ref.current) return
    const items = [...ref.current.querySelectorAll<HTMLElement>(FOCUSABLE)].filter((x) => x.offsetParent !== null)
    if (!items.length) return
    const first = items[0]
    const last = items[items.length - 1]
    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault()
      last.focus()
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault()
      first.focus()
    }
  }

  const width = size === 'md' ? 'sm:max-w-xl' : size === 'lg' ? 'sm:max-w-3xl' : 'sm:max-w-6xl'
  return createPortal(
    <div className="fixed inset-0 z-50 flex items-stretch justify-center bg-[#0d1f30]/45 p-2 backdrop-blur-[2px] sm:items-center sm:p-6" onMouseDown={(e) => e.target === e.currentTarget && requestClose()}>
      <div
        ref={ref}
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
        tabIndex={-1}
        onKeyDown={onKeyDown}
        className={`flex max-h-full w-full flex-col overflow-hidden rounded-2xl bg-white shadow-[0_24px_64px_rgba(13,31,48,0.35)] outline-none sm:max-h-[90vh] ${width}`}
      >
        <header className="flex items-start justify-between gap-4 border-b border-line px-5 py-4 sm:px-6">
          <div className="min-w-0">
            <h2 id="modal-title" className="text-lg font-semibold tracking-tight text-ink">
              {title}
            </h2>
            {subtitle && <div className="mt-0.5 text-sm text-muted">{subtitle}</div>}
          </div>
          <button type="button" onClick={requestClose} aria-label="Cerrar" className="-mr-2 cursor-pointer rounded-lg p-2 text-muted hover:bg-mist hover:text-ink">
            <X className="size-5" aria-hidden />
          </button>
        </header>
        <div className="min-h-0 flex-1 overflow-y-auto px-5 py-5 sm:px-6">{children}</div>
        {footer && <footer className="flex flex-wrap items-center justify-end gap-2 border-t border-line bg-[#fafcfd] px-5 py-3.5 sm:px-6">{footer}</footer>}
      </div>
    </div>,
    document.body,
  )
}
