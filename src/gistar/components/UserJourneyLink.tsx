import { Route } from 'lucide-react'

export function UserJourneyLink({ className = 'text-ink hover:bg-mist' }: { className?: string }) {
  return (
    <a href={`${import.meta.env.BASE_URL}user-journey.html`} target="_blank" rel="noopener noreferrer"
      aria-label="Recorrido de usuario (abre en otra pestaña)"
      className={`inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium underline underline-offset-4 ${className}`}>
      <Route className="size-4" aria-hidden />
      Recorrido de usuario
    </a>
  )
}
