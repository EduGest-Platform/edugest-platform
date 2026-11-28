const accessViews = [
  { id: 'login', es: 'Iniciar sesión', en: 'Sign in' },
  { id: 'inscripcion', es: 'Quiero inscribirme', en: 'Apply for a course' },
  { id: 'catalogo', es: 'Ver formaciones', en: 'Browse courses' },
] as const

export type PublicAccessView = (typeof accessViews)[number]['id']

export function PublicAccessNavigation({ view, onNavigate, language = 'es' }: {
  view: PublicAccessView
  language?: 'es' | 'en'
  onNavigate: (view: PublicAccessView) => void
}) {
  return (
    <nav lang={language} aria-label={language === 'en' ? 'Public access' : 'Acceso público'} className="flex flex-wrap gap-2">
      {accessViews.map(({ id, es, en }) => (
        <button
          key={id}
          type="button"
          aria-current={view === id ? 'page' : undefined}
          onClick={() => onNavigate(id)}
          className={`min-h-10 rounded-lg border px-3 text-sm font-semibold transition-colors ${
            view === id ? 'border-navy bg-navy text-white' : 'border-line bg-white text-navy hover:bg-mist'
          }`}
        >
          {language === 'en' ? en : es}
        </button>
      ))}
    </nav>
  )
}
