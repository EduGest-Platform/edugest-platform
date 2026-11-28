# KAN-38 — Evidencia de aceptación de personal / Staff acceptance evidence

27/11/2026 · Owner Elizabeth · Cross-review Yohanna. Snapshot: merge #270 d6692d7, #271 6002007; inspected dev through GitHub. Documentation only; no local runtime, no real accounts or deployment.

## ES
| Criterio | Evidencia | Estado |
|---|---|---|
| Ficha vinculada a cuenta interna | #145, #156–160, #270; StaffProfile/User, aceptación propia | Implementado para cuentas existentes; alta de identidad nueva no demostrada |
| Invitación única, caducable y revocable | #270, staff/service.py, invitation_directory.py, test_staff_invitation_directory.py | CI/E2E del PR PASS; renovación invalida anterior, caducidad y reutilización rechazadas |
| Separar ficha y privilegios | #270; solicitud, revisión y aplicación explícita separadas, sin autorrevisión | CI/E2E PASS para recorrido sintético |
| Revocación auditable | #270; application_service.py, assignment_history.py y test_staff_access_revocation.py | CI/E2E PASS; historial conservado |
| Excluir aspirantes/coders/alumni | política de cuentas internas y directorio; suite de API #270 | Verificar matriz negativa completa con revisora |
| Fundación puede enviar invitación | KAN-222; captacion no tiene autoridad de emisión actualmente | BLOCKED: decisión de alcance e implementación, no ampliar permisos automáticamente |

Subtareas en Jira al revisar: KAN-223 Finalizada; KAN-225 En curso; KAN-230 En curso; KAN-232 Idea; KAN-222 Idea. #270 integra UI, ciclo de invitación y aplicación/revocación, pero no demuestra envío institucional, creación de cuentas nuevas ni autorización delegada. No cerrar historia ni subtareas ajenas por inferencia.

Pruebas observadas en GitHub: [CI #270](https://github.com/EduGest-Platform/edugest-platform/actions/runs/46030588824), [F1 E2E #270](https://github.com/EduGest-Platform/edugest-platform/actions/runs/46030588791), paso Staff invitation rotation and acceptance PASS. [CI #271](https://github.com/EduGest-Platform/edugest-platform/actions/runs/46032355814) y [E2E #271](https://github.com/EduGest-Platform/edugest-platform/actions/runs/46032355812) conservan el paso de personal. No se ejecutaron pruebas nuevas. Evidencia histórica de CI, no certificación de staging.

Cierre: confirmar KAN-222, alcance alta/envío con PO, revisión cruzada de matriz negativa y resultados, actualizar KAN-225/230/232 por sus responsables; comprobar CI en HEAD integrado y aceptación. No activar correo ni cuentas reales.

## EN
The merged staff workflow covers existing internal accounts, expiring/rotatable one-time invitations, separate review/application of scoped roles, conflict recovery, and auditable revocation. The cited CI and browser steps passed on PR heads, including the staff regression in #271. These are observed remote results, not fresh local runs or staging certification. New identity onboarding and institutional delivery are not demonstrated. Foundation issuance authority remains unresolved (KAN-222). Verify the negative role matrix, reconcile the four open subtasks with their owners, and obtain PO acceptance and Yohanna's cross-review before closing. No permission or deployment changes in this report.
