/**
 * Import boundaries of the web app (KAN-96), checked on the source text so they cannot drift silently.
 * See docs/reports/KAN-96-import-boundaries.md for the reasons behind each rule.
 */
import { readdirSync, readFileSync } from 'node:fs'
import { dirname, join, relative, resolve, sep } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

const SRC_DIR = resolve(dirname(fileURLToPath(import.meta.url)), '../..')
const IMPORT_PATTERN = /^\s*(import|export)\s+(type\s+)?[^'"]*?from\s+['"]([^'"]+)['"]/gm
const ALLOWED_PACKAGES = new Set(['react', 'react-dom', 'react-dom/client', 'lucide-react', 'openapi-fetch', 'vitest'])
const HTTP_CLIENT = 'shared/api/client.ts'

type SourceImport = { file: string; target: string; typeOnly: boolean }

function sourceFiles(dir: string): string[] {
  return readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const path = join(dir, entry.name)
    if (entry.isDirectory()) return sourceFiles(path)
    return /\.(ts|tsx)$/.test(entry.name) && !entry.name.endsWith('.gen.ts') ? [path] : []
  })
}

function toSrcPath(path: string): string {
  return relative(SRC_DIR, path).split(sep).join('/')
}

function importsOf(file: string): SourceImport[] {
  const text = readFileSync(file, 'utf8')
  return [...text.matchAll(IMPORT_PATTERN)].map((match) => ({
    file: toSrcPath(file),
    target: match[3],
    typeOnly: Boolean(match[2]),
  }))
}

function resolvedTarget(item: SourceImport): string {
  const base = resolve(SRC_DIR, dirname(item.file), item.target)
  const path = toSrcPath(base)
  return /\.(ts|tsx|json|css)$/.test(path) ? path : `${path}.ts`
}

const ALL_IMPORTS = sourceFiles(SRC_DIR).flatMap(importsOf)
const RELATIVE_IMPORTS = ALL_IMPORTS.filter((item) => item.target.startsWith('.'))

describe('web import boundaries (KAN-96)', () => {
  it('finds the source files it checks', () => {
    expect(ALL_IMPORTS.length).toBeGreaterThan(50)
  })

  it('never imports code from outside src/ (api, ml, e2e, infra)', () => {
    const escaping = RELATIVE_IMPORTS.filter((item) => resolvedTarget(item).startsWith('..'))
    expect(escaping).toEqual([])
  })

  it('uses only the declared runtime packages', () => {
    const packages = ALL_IMPORTS.filter((item) => !item.target.startsWith('.') && !item.target.startsWith('@/'))
    const isTestTool = (item: SourceImport) => item.file.includes('/__tests__/') && item.target.startsWith('node:')
    expect(packages.filter((item) => !ALLOWED_PACKAGES.has(item.target) && !isTestTool(item))).toEqual([])
  })

  it('calls the HTTP client only from API views and the shared API layer', () => {
    const callers = RELATIVE_IMPORTS.filter((item) => resolvedTarget(item) === HTTP_CLIENT).map((item) => item.file)
    expect(callers.filter((file) => !file.startsWith('gistar/views/api/') && !file.startsWith('shared/api/'))).toEqual([])
  })

  it('keeps shared/ independent of gistar/ except for type-only imports', () => {
    const reverse = RELATIVE_IMPORTS.filter(
      (item) => item.file.startsWith('shared/') && resolvedTarget(item).startsWith('gistar/') && !item.typeOnly,
    )
    expect(reverse).toEqual([])
  })
})
