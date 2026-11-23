# KAN-212 — Local fallback runbook / Runbook de respaldo local

**Owner / Responsable:** Yohanna. **Reviewer / Revisor solicitado:** Anas. **Deadline:** 27/11/2026. **Source snapshot / Base:** `dev@7f834ef`, 23/11/2026. Source-checked instructions, not a new deployment authorization / instrucciones contrastadas con código, no autorización de despliegue.

## ES — Preparación y arranque

El plan B es el stack local de [Compose](../../infra/compose.yaml): PostgreSQL, API, web y MLflow, con datos sintéticos propios. No recupera automáticamente una base remota ni es un dump/backup de PostgreSQL. Para recuperar datos haría falta un procedimiento de backup/restauración aceptado, fuera de este incremento.

Prerequisitos: Docker con Compose y daemon local, puertos 5432/8000/8443/5000 libres, Bash, curl y Python 3. Desde la raíz del repo, preparar `infra/.env` con las variables de `infra/.env.example` y secretos locales; no copiarlos a chat, capturas o logs. La primera construcción requiere red para imágenes/dependencias; el arranque offline no se da por garantizado solo por existir el YAML.

Validar primero sin imprimir la configuración resuelta:

```sh
docker compose -f infra/compose.yaml config --quiet
```

Arranque de un comando, después de esa preparación:

```sh
docker compose -f infra/compose.yaml up -d --build --wait
```

Esto sí inicia servicios locales, aplica las migraciones pendientes al arrancar API y reconcilia seed sintético mediante el entrypoint existente. No ejecutar contra un contexto Docker remoto ni usarlo como rollback automático de esquema. Si falla una migración, detener el diagnóstico y conservar el volumen; no reiniciar el seed con reset.

Comprobar luego:

```sh
bash infra/smoke-test.sh
```

El smoke comprueba health de API/BD, docs, web, ruta SPA, MLflow y login sintético. Las URLs locales son web `http://localhost:8443`, API `http://localhost:8000/docs`, MLflow `http://localhost:5000`. Los puertos publicados en el Compose inspeccionado están ligados a loopback.

El smoke usa `python3` para serializar el login correctamente. Si el ejecutable se llama `python` (por ejemplo, Git Bash en Windows): `PYTHON_BIN=python bash infra/smoke-test.sh`. El cuerpo JSON va por stdin de curl, sin contraseña en sus argumentos. Las respuestas de login se suprimen en la comprobación y no se guardan tokens.

Si se proporciona `DEMO_PASSWORD`, debe ser el valor efectivo exacto y no una representación entrecomillada de dotenv. La lectura heredada de `infra/.env` sigue siendo simple: no interpreta interpolación ni toda la gramática dotenv. Para valores con esa sintaxis, suministrar el valor efectivo mediante el entorno del proceso, sin imprimirlo. Este cambio no implementa un parser dotenv completo.

## ES — Si algo falla

| Síntoma | Siguiente comprobación | Límite |
|---|---|---|
| Compose no valida | Variables requeridas presentes, ruta del archivo, versión de Compose | No usar `config` sin `--quiet` para pegar resultados: podría expandir secretos |
| Puerto ocupado | Identificar el proceso local y acordar liberarlo | No terminar procesos ajenos automáticamente |
| API/BD no saludables | `docker compose -f infra/compose.yaml ps`; revisar logs localmente | No publicar logs crudos; compartir solo estado, SHA y request_id seguro |
| Login FAIL | Contraseña efectiva y `PYTHON_BIN`; estado del resto de checks | No pegar password, cuerpo de login ni token |
| Web carga sin datos | URL de API usada en build y modo de datos | localStorage/demo no confirma persistencia backend |
| Necesidad de parar | `docker compose -f infra/compose.yaml stop` | Conserva volúmenes; borrar volúmenes no es recuperación |

Registrar fecha, SHA, plataforma, checks PASS/FAIL y limitaciones sin valores secretos. No concluir que CI verde prueba este PC ni que el smoke confirma todos los recorridos del producto.

## EN — Preparation and single-command fallback

This uses the existing local synthetic Compose stack, not a remote database restore or PostgreSQL backup. Prerequisites are a local Docker daemon/Compose, free published ports, Bash, curl and Python 3. Prepare ignored `infra/.env` from its template with local secrets; first build may require network. Validate with `config --quiet`, then use the single `up -d --build --wait` command above.

API startup applies pending migrations and reconciles the synthetic seed. Do not target a remote Docker context or treat restart as schema rollback. Preserve volumes when investigating migration failures. Run the smoke separately: it checks API/database health, docs, web/SPA, MLflow and synthetic login. Source-published ports bind loopback; that is not proof services were started here.

The login JSON is serialized by Python and piped to curl stdin, without a password argument; check output suppresses login bodies/tokens. `PYTHON_BIN=python` supports hosts without a `python3` executable. The inherited dotenv reader is not a full parser: for quoted/interpolated dotenv syntax, supply the exact resolved password in the process environment without printing it. No broad dotenv compatibility is claimed.

On failure, inspect local status and prerequisites without posting raw logs/config/passwords. Distinguish frontend demo data from server persistence. `compose stop` preserves volumes; deleting volumes is not recovery. Record date, commit, platform and individual PASS/FAIL results. Product flows and deployment/backup acceptance remain separate.

## Actual validation / Validación realizada

Local: three CLI regression tests passed (six special-character payloads plus empty/invalid-UTF-8 paths), Ruff passed, Bash syntax check passed and links/diff checked. No Docker stack, database migration, remote deployment or full smoke was run in this task. CI completion is not checked, per user instruction. / No se declara ejecutado el stack ni el despliegue; CI no esperado.
