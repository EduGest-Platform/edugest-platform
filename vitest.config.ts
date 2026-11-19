/**
 * Vitest configuration, separate from the Figma Make `vite.config.ts`.
 *
 * Unit tests need neither the React plugin nor the Make plugins, only the `@` alias.
 * The file avoids `__dirname` and JSON imports so Vitest can load it with
 * `--configLoader runner`, which does not write a bundled copy to
 * `node_modules/.vite-temp`. A locked `.vite-temp` caused the Windows EPERM (KAN-87).
 */
import { fileURLToPath } from "node:url"
import { defineConfig } from "vitest/config"

export default defineConfig({
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  test: {
    include: ["src/**/*.test.{ts,tsx}"],
  },
})
