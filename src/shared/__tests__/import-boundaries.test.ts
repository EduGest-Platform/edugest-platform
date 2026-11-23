/**
 * Import boundaries of the web app (KAN-96), checked on the source text so they cannot drift silently.
 * See docs/reports/KAN-96-import-boundaries.md for the reasons behind each rule.
 */
import { readdirSync, readFileSync } from 'node:fs'
import { dirname, join, relative, resolve, sep } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

const SRC_DIR = resolve(dirname(fileURLToPath(import.meta.url)), '../..')
// Static `import … from` / `export … from`, side-effect `import 'x'` and dynamic `import('x')` with a literal path.
const STATIC_IMPORT_PATTERN = /^\s*(?:import|export)\s+(type\s+)?[^'"]*?from\s+['"]([^'"]+)['"]/gm
const SIDE_EFFECT_IMPORT_PATTERN = /^\s*import\s+['"]([^'"]+)['"]/gm
const DYNAMIC_IMPORT_PATTERN = /\bimport\(\s*['"]([^'"]+)['"]\s*\)/g
const SRC_ALIAS = '@/'
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

/** Every import of a source text; `file` is its path relative to src/. */
function parseImports(file: string, text: string): SourceImport[] {
  const staticImports = [...text.matchAll(STATIC_IMPORT_PATTERN)].map((match) => ({
    file,
    target: match[2],
    typeOnly: Boolean(match[1]),
  }))
  const otherImports = [...text.matchAll(SIDE_EFFECT_IMPORT_PATTERN), ...text.matchAll(DYNAMIC_IMPORT_PATTERN)].map(
    (match) => ({ file, target: match[1], typeOnly: false }),
  )
  return [...staticImports, ...otherImports]
}

/** Relative imports and the `@/` alias point into the project; everything else is a package. */
function isProjectImport(item: SourceImport): boolean {
  return item.target.startsWith('.') || item.target.startsWith(SRC_ALIAS)
}

/** Path relative to src/ of a project import, with the `@/` alias resolved like Vite and tsconfig do. */
function resolvedTarget(item: SourceImport): string {
  const base = item.target.startsWith(SRC_ALIAS)
    ? resolve(SRC_DIR, item.target.slice(SRC_ALIAS.length))
    : resolve(SRC_DIR, dirname(item.file), item.target)
  const path = toSrcPath(base)
  return /\.(ts|tsx|json|css)$/.test(path) ? path : `${path}.ts`
}

function isAllowedPackage(item: SourceImport): boolean {
  const isTestFile = item.file.includes('/__tests__/')
  const isTestTool = item.target.startsWith('node:') || item.target === 'react-dom/server'
  return ALLOWED_PACKAGES.has(item.target) || (isTestFile && isTestTool)
}

function callsHttpClientOutsideApiLayers(imports: SourceImport[]): SourceImport[] {
  return imports.filter(
    (item) =>
      resolvedTarget(item) === HTTP_CLIENT &&
      !item.typeOnly &&
      !item.file.startsWith('gistar/views/api/') &&
      !item.file.startsWith('shared/api/'),
  )
}

function sharedRuntimeImportsOfGistar(imports: SourceImport[]): SourceImport[] {
  return imports.filter(
    (item) => item.file.startsWith('shared/') && resolvedTarget(item).startsWith('gistar/') && !item.typeOnly,
  )
}

// This checker is skipped: its regression fixtures are import statements written as strings.
const CHECKER_FILE = fileURLToPath(import.meta.url)
const ALL_IMPORTS = sourceFiles(SRC_DIR)
  .filter((file) => resolve(file) !== resolve(CHECKER_FILE))
  .flatMap((file) => parseImports(toSrcPath(file), readFileSync(file, 'utf8')))
const PROJECT_IMPORTS = ALL_IMPORTS.filter(isProjectImport)

describe('web import boundaries (KAN-96)', () => {
  it('finds the source files it checks', () => {
    expect(ALL_IMPORTS.length).toBeGreaterThan(50)
  })

  it('never imports code from outside src/ (api, ml, e2e, infra)', () => {
    const escaping = PROJECT_IMPORTS.filter((item) => resolvedTarget(item).startsWith('..'))
    expect(escaping).toEqual([])
  })

  it('uses only the declared runtime packages', () => {
    const packages = ALL_IMPORTS.filter((item) => !isProjectImport(item))
    expect(packages.filter((item) => !isAllowedPackage(item))).toEqual([])
  })

  it('calls the HTTP client only from API views and the shared API layer', () => {
    expect(callsHttpClientOutsideApiLayers(PROJECT_IMPORTS)).toEqual([])
  })

  it('keeps shared/ independent of gistar/ except for type-only imports', () => {
    expect(sharedRuntimeImportsOfGistar(PROJECT_IMPORTS)).toEqual([])
  })
})

describe('import boundary checker regressions (KAN-96)', () => {
  it('rejects undeclared packages even in test directories', () => {
    expect(isAllowedPackage({ file: 'gistar/__tests__/render.test.tsx', target: 'undeclared-package', typeOnly: false })).toBe(false)
    expect(isAllowedPackage({ file: 'gistar/views/Render.tsx', target: 'undeclared-package', typeOnly: false })).toBe(false)
  })

  const projectImportsOf = (file: string, lines: string[]) =>
    parseImports(file, lines.join('\n')).filter(isProjectImport)

  it('allows the React server renderer only in test directories', () => {
    const statement = "import { renderToStaticMarkup } from 'react-dom/server'"
    const testImports = parseImports('gistar/__tests__/silenceReview.test.tsx', statement)
    const runtimeImports = parseImports('gistar/views/Dashboard.tsx', statement)

    expect(testImports.filter(isAllowedPackage)).toHaveLength(1)
    expect(runtimeImports.filter(isAllowedPackage)).toEqual([])
  })

  it('flags the HTTP client imported through the @/ alias', () => {
    const imports = projectImportsOf('gistar/views/Dashboard.tsx', ["import { api } from '@/shared/api/client'"])
    expect(callsHttpClientOutsideApiLayers(imports)).toHaveLength(1)
  })

  it('flags the HTTP client imported with a literal dynamic import', () => {
    const imports = projectImportsOf('gistar/views/Dashboard.tsx', ["const m = await import('../../shared/api/client')"])
    expect(callsHttpClientOutsideApiLayers(imports)).toHaveLength(1)
  })

  it('flags shared/ importing gistar/ at runtime through the alias, dynamically or for side effects', () => {
    const imports = projectImportsOf('shared/ui/Widget.tsx', [
      "import { x } from '@/gistar/state'",
      "const y = import('@/gistar/views/Home')",
      "import '../../gistar/setup'",
    ])
    expect(sharedRuntimeImportsOfGistar(imports)).toHaveLength(3)
  })

  it('still allows type-only imports from shared/ to gistar/ via the alias', () => {
    const imports = projectImportsOf('shared/ui/Widget.tsx', ["import type { Role } from '@/gistar/types'"])
    expect(sharedRuntimeImportsOfGistar(imports)).toEqual([])
  })

  it('allows type-only imports of the client (they make no HTTP call)', () => {
    const imports = projectImportsOf('gistar/__tests__/server.test.ts', ["import type { Schemas } from '../../shared/api/client'"])
    expect(callsHttpClientOutsideApiLayers(imports)).toEqual([])
  })

  it('allows the API layers to use the client through the alias', () => {
    const imports = projectImportsOf('gistar/views/api/Calls.tsx', ["import { api } from '@/shared/api/client'"])
    expect(callsHttpClientOutsideApiLayers(imports)).toEqual([])
  })
})
