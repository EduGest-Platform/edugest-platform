import { useEffect, useState } from 'react'
import { Moon, Sun } from 'lucide-react'

type Language = 'es' | 'en'
type Theme = 'light' | 'dark'

function preference(key: string): string | null {
  try { return localStorage.getItem(key) } catch { return null }
}

export function AppearanceControls() {
  const [language, setLanguage] = useState<Language>(() => preference('edugest.language') === 'en' ? 'en' : 'es')
  const [theme, setTheme] = useState<Theme>(() => {
    const saved = preference('edugest.theme')
    return saved === 'dark' || saved === 'light' ? saved : window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
  })
  useEffect(() => {
    try {
      localStorage.setItem('edugest.language', language)
      localStorage.setItem('edugest.theme', theme)
    } catch { /* Preferences remain usable without storage. */ }
  }, [language, theme])
  const en = language === 'en'
  const dark = theme === 'dark'
  return <section aria-label={en ? 'Appearance preview' : 'Vista previa de apariencia'} lang={language}
    className="grid gap-3 rounded-xl border p-4"
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
    <h2 className="font-semibold">{en ? 'Welcome to EduGest' : 'Bienvenido a EduGest'}</h2>
    <p className="text-sm">{en ? 'Preview only. Global translation and theme are pending.' : 'Vista previa. Traducción y tema globales pendientes.'}</p>
  </section>
}
