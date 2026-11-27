import { useEffect, useState } from 'react'
import { Moon, Sun } from 'lucide-react'

export type Language = 'es' | 'en'
export type Theme = 'light' | 'dark'

function preference(key: string): string | null {
  try { return localStorage.getItem(key) } catch { return null }
}

export function useAppearance() {
  const [language, setLanguage] = useState<Language>(() => preference('edugest.language') === 'en' ? 'en' : 'es')
  const [theme, setTheme] = useState<Theme>(() => {
    const saved = preference('edugest.theme')
    return saved === 'dark' || saved === 'light' ? saved : typeof window !== 'undefined' && typeof window.matchMedia === 'function' && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
  })
  useEffect(() => {
    document.documentElement.dataset.theme = theme
    // Most screens remain Spanish; mark translated controls/regions individually instead.
    document.documentElement.lang = 'es'
    try {
      localStorage.setItem('edugest.language', language)
      localStorage.setItem('edugest.theme', theme)
    } catch { /* Preferences remain usable without storage. */ }
  }, [language, theme])
  return { language, setLanguage, theme, setTheme }
}

export function AppearanceControls({ language, setLanguage, theme, setTheme }: ReturnType<typeof useAppearance>) {
  const en = language === 'en'
  const dark = theme === 'dark'
  return <section aria-label={en ? 'Appearance preferences' : 'Preferencias de apariencia'} lang={language}
    className="flex items-center gap-2 rounded-lg border p-1"
    style={{ background: dark ? '#142b46' : '#ffffff', color: dark ? '#ffffff' : '#142b46', colorScheme: theme }}>
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div role="group" aria-label={en ? 'Language' : 'Idioma'} className="flex gap-2">
        <button type="button" lang="es" aria-pressed={!en} onClick={() => setLanguage('es')} className="rounded border px-3 py-2" style={{ fontWeight: !en ? 700 : 400 }}>ES</button>
        <button type="button" lang="en" aria-pressed={en} onClick={() => setLanguage('en')} className="rounded border px-3 py-2" style={{ fontWeight: en ? 700 : 400 }}>EN</button>
      </div>
      <button type="button" aria-pressed={dark} onClick={() => setTheme(dark ? 'light' : 'dark')} className="flex items-center gap-2 rounded border px-3 py-2">
        {dark ? <Moon size={18} aria-hidden /> : <Sun size={18} aria-hidden />}
        {en ? 'Night mode' : 'Modo noche'}
      </button>
    </div>

  </section>
}
