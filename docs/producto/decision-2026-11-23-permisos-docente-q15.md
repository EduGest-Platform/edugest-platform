# Decisión PO 23/11/2026 — Permisos del docente (Melissa, ronda 3, Q15) / PO decision — teacher permissions

**ES.** Melissa (Q15): «Lo relacionado con el perfil de coordinación se lo trasladaría al perfil de docente. Los permisos por cohorte los podría también ajustar la persona de perfil docente». Lo aprobó la PO el 23/11/2026.

Implementación (`api/app/core/authz.py`, `api/app/modules/learning/team_router.py`):
- El docente recibe las atribuciones académicas de coordinación: indicadores agregados de asistencia, entregas y competencias de sus cohortes (`*.aggregate`). Ya tenía, además, el detalle por persona.
- El docente gestiona el equipo docente de sus cohortes: `GET/PUT/DELETE /cohorts/{id}/teaching-team/{user_id}`. Solo puede conceder el rol `docente` en esa cohorte, a cuentas de personal (nunca a personas candidatas ni coders). No puede quitar a la última persona docente. Cada cambio queda auditado.
- **No cambia:** la decisión final de admisión y la matrícula siguen en Selección y Coordinación con quórum de 2 (Q4, Q11, Q12). El rol `coordinacion` se mantiene.

**EN.** Melissa (Q15) asked to move the coordination attributions to the teacher, and to let teachers adjust permissions per cohort. The PO approved it on 23/11/2026. Teachers now get the academic aggregate indicators of their cohorts and manage their cohort's teaching team. They can only grant `docente` on that cohort, only to staff accounts, cannot remove the last teacher, and every change is audited. The admission decision and the enrollment stay with selection and coordination (quorum of 2). The `coordinacion` role is kept.
