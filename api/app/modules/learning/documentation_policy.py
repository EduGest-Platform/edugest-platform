from app.core.authz import Scope
from app.core.errors import UserFacingError
from app.modules.learning.access import cohort_scope


def require_documentation_admin(actor):
    # Use existing global administration; no new grants to recruiting or teaching roles.
    actor.require('enrollment.documentation.manage', Scope())


def require_reader_role(actor):
    global_access, programs, calls = actor.scopes_for('applications.read')
    if actor.user.person_id is None and not (global_access or programs or calls):
        actor.require('applications.read', Scope())


def enrollment_not_found():
    return UserFacingError(404, 'enrollment_not_found', 'No encontramos esta matrícula. Comprueba el identificador y vuelve a intentarlo.')


def require_documentation_read(actor, enrollment, cohort):
    if actor.user.person_id == enrollment.person_id:
        return
    scope = cohort_scope(cohort)
    if actor.user.person_id is not None and not actor.can('applications.read', scope):
        raise enrollment_not_found()
    actor.require('applications.read', scope)


def check_documentation_version(enrollment, expected):
    if enrollment.documentation_version != expected:
        raise UserFacingError(409, 'documentation_version_conflict', 'La documentación ha cambiado. Actualiza la matrícula antes de volver a intentarlo.')


def require_accreditation_eligibility(enrollment, application, cohort, has_admission):
    coherent = (enrollment.estado == 'activa' and application is not None and cohort is not None
                and application.id == enrollment.application_id and application.person_id == enrollment.person_id
                and application.stage == 'admitida' and cohort.id == enrollment.cohort_id
                and cohort.call_id == application.call_id and has_admission)
    if not coherent:
        raise UserFacingError(409, 'documentation_admission_required',
                              'Se necesita una matrícula activa con admisión y cohorte verificables. Revisa la trazabilidad de la matrícula antes de acreditar documentación.')
