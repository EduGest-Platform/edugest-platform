# Skills de frontend del equipo / Team frontend skills

**ES:** Instrucciones cortas para el asistente de IA, para que su ayuda siga las reglas de EduGest. Claude Code las carga solas desde esta carpeta. Se cambian con una PR, como el resto del código.

**EN:** Short instruction files for the AI assistant, so its help follows EduGest's rules. Claude Code loads them from this folder automatically. Change them with a PR, like any other code.

| Skill | Para qué / What for | Cuándo / When |
|---|---|---|
| `edugest-frontend-conventions` | Stack, carpetas, código, datos honestos, SEO de páginas públicas / stack, folders, code, honest data, public-page SEO | Siempre / always |
| `edugest-ux-accessibility` | Accesibilidad, tono humano, decisiones humanas / accessibility, human tone, human decisions | Siempre / always |
| `edugest-pr-committee` | Revisión de PR en 5 áreas, incluida seguridad / PR review in 5 areas, including security | Desde la primera PR / from the first PR |
| `edugest-performance` | Carga rápida y ligera / fast, light loading | S3, antes de la congelación / before the freeze |
| `edugest-motion` | Animaciones y transiciones / animations and transitions | Solo si hay tiempo / only if there is time |

## Scripts de revisión / Review scripts

**ES:** `edugest-pr-committee/scripts/` tiene los comandos que usa la revisión, para que todo el equipo compruebe lo mismo: `review-worktree.sh` (copia aislada de la PR, con su rama base real), `review-web.sh`, `review-api.sh` (base de datos y entorno de Python temporales), `review-ci.sh`, `contrast.mjs` y `review-cleanup.sh`. Lee siempre los scripts nuevos de una PR antes de ejecutarlos.

**EN:** `edugest-pr-committee/scripts/` holds the commands the review uses, so everyone checks the same things: `review-worktree.sh` (isolated copy of the PR, with its real base branch), `review-web.sh`, `review-api.sh` (throwaway database and Python environment), `review-ci.sh`, `contrast.mjs` and `review-cleanup.sh`. Always read a PR's new scripts before running them.
