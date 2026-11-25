const accessViews = [
  { id: 'login', label: 'Iniciar sesión' },
  { id: 'inscripcion', label: 'Quiero inscribirme' },
  { id: 'catalogo', label: 'Ver formaciones' },
] as const

export type PublicAccessView = (typeof accessViews)[number]['id']

export function PublicAccessNavigation({ view, onNavigate }: {
  view: PublicAccessView
  onNavigate: (view: PublicAccessView) => void
}) {
  return (
    <nav aria-label="Acceso público" className="flex flex-wrap gap-2">
      {accessViews.map(({ id, label }) => (
        <button
          key={id}
          type="button"
          aria-current={view === id ? 'page' : undefined}
          onClick={() => onNavigate(id)}
          className={`min-h-10 rounded-lg border px-3 text-sm font-semibold transition-colors ${
            view === id ? 'border-navy bg-navy text-white' : 'border-line bg-white text-navy hover:bg-mist'
          }`}
        >
          {label}
        </button>
      ))}
    </nav>
  )
}
