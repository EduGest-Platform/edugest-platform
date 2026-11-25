# Contrato vigente de inscripción pública / Current public intake contract

**KAN-111 · KAN-231 · KAN-112 · KAN-132** · 25/11/2026

## Registro que funciona hoy / Registration currently supported

La fuente ejecutable es `ApplicationCreate` en `api/app/modules/admissions/schemas.py`, publicada como OpenAPI. Esta tabla comprueba el alcance del formulario vigente. El [diccionario consolidado](kan-107-1-diccionario-datos-consolidado.md) mantiene las decisiones de producto para las ampliaciones.

The executable source is `ApplicationCreate` in `api/app/modules/admissions/schemas.py`, published as OpenAPI. This table checks the scope of the current form. The [consolidated dictionary](kan-107-1-diccionario-datos-consolidado.md) tracks the product decisions for future fields.

| Campo / Field | Contrato vigente / Current contract | Destino / Destination |
|---|---|---|
| `call_id` | Identificador de oferta de 1–30 caracteres con al menos un carácter visible. El alta exige que la oferta esté publicada y abierta. / Offer ID of 1–30 characters with at least one non-whitespace character. Registration requires a published, open offer. | Candidatura / Application |
| `nombre` | 2–120 caracteres tras recortar extremos. / 2–120 characters after trimming. | Ficha de persona al crearla. / Person record on creation. |
| `email` | Correo normalizado y validado. Identidad única por correo y candidatura única por persona y convocatoria. / Normalized, validated email. One person per email and one application per person and call. | Ficha de persona / Person record |
| `motivacion` | 10–2000 caracteres tras recortar extremos. / 10–2000 characters after trimming. | Candidatura / Application |
| `disponibilidad` | `Mañana`, `Tarde`, `Flexible`. | Candidatura / Application |
| `acepta_datos_sinteticos` | Confirmación obligatoria con el valor booleano JSON `true`. / Required acknowledgement with the JSON boolean value `true`. | Candidatura / Application |

## Campos pendientes de implementación / Fields awaiting implementation

- Teléfono, año de nacimiento, provincia o localidad, nacionalidad, género, experiencia, acceso a ordenador o internet y situación actual se documentan por formulario en el [inventario canónico](diccionario-campos-candidatura.md). Sus decisiones y condiciones vigentes se consultan en el diccionario consolidado. / The [canonical inventory](diccionario-campos-candidatura.md) records phone, birth year, province or locality, nationality, gender, experience, computer or internet access and current situation by form. The consolidated dictionary holds the current decisions and conditions.
- Hace falta validar la configuración de cada convocatoria, incluyendo opciones, obligatoriedad, acceso y retención, antes de incorporar nuevos campos a la captura. Los campos adicionales al contrato actual se descartan al validar el cuerpo. / Validate each call's options, required fields, access and retention before adding fields to intake. Request validation discards fields outside the current contract.
- Los requisitos de campaña se gestionan en las definiciones versionadas por convocatoria. Las excepciones requieren revisión humana. / Campaign requirements use versioned call definitions. Exceptions require human review.

## Comprobación HTTP / HTTP verification

ES — El recorrido configura un requisito obligatorio en una convocatoria sintética publicada, rechaza una confirmación numérica y envía dos solicitudes concurrentes con variantes del mismo correo. La candidatura queda enviada con una revisión pendiente. Comprueba la denegación fuera de ámbito y registra la excepción mediante revisión humana, conservando la etapa de la candidatura.

EN — The journey configures a mandatory requirement for a published synthetic call, rejects a numeric acknowledgement and submits concurrent requests with variants of the same email address. The application stays submitted with a pending review. It checks out-of-scope denial and records an exception through human review while preserving the application stage.

Con FastAPI y PostgreSQL sintéticos desechables, exporta la misma contraseña de demo que usa la API. / With disposable synthetic FastAPI and PostgreSQL services, export the same demo password used by the API.

```sh
GISTAR_API=http://localhost:8000 node e2e/intake-human-review.mjs
```
