from app.core import audit
from app.core.db import utcnow
from app.core.errors import UserFacingError
from sqlalchemy import func, select
from app.modules.admissions.models import Application
from app.modules.catalog.models import Cohort
from app.modules.audit.models import AuditEvent
from app.modules.learning.documentation_policy import enrollment_not_found, require_documentation_read, require_reader_role
from app.modules.learning.documentation_policy import check_documentation_version, require_accreditation_eligibility, require_documentation_admin
from app.modules.learning.documentation_schemas import DocumentationHistoryItem, DocumentationOut
from app.modules.learning.models import Enrollment
from app.modules.selection.models import SelectionDecision


def documentation_out(row):
    return DocumentationOut(enrollment_id=row.id, state=row.documentation_state,
                            version=row.documentation_version, accredited_at=row.documentation_accredited_at)


def readable_enrollment(db, actor, enrollment_id):
    require_reader_role(actor)
    row = db.get(Enrollment, enrollment_id)
    if row is None:
        raise enrollment_not_found()
    cohort = db.get(Cohort, row.cohort_id)
    if cohort is None:
        raise enrollment_not_found()
    require_documentation_read(actor, row, cohort)
    return row


def read_documentation(db, actor, enrollment_id):
    row = readable_enrollment(db, actor, enrollment_id)
    audit.record(db, actor, 'enrollment.documentation_viewed', 'enrollment', str(row.id))
    db.commit()
    return documentation_out(row)


def locked_documentation(db, actor, enrollment_id):
    require_documentation_admin(actor)
    application_id = db.scalar(select(Enrollment.application_id).where(Enrollment.id == enrollment_id))
    # Match admission's lock order: application before enrollment. No admission state is changed here.
    application = None if application_id is None else db.scalar(
        select(Application).where(Application.id == application_id).with_for_update())
    row = db.scalar(select(Enrollment).where(Enrollment.id == enrollment_id).with_for_update().execution_options(populate_existing=True))
    if row is None:
        raise enrollment_not_found()
    if row.application_id != application_id:
        raise UserFacingError(409, 'enrollment_mapping_changed', 'La matrícula ha cambiado. Actualiza su información antes de continuar.')
    return row, application


def accredit_documentation(db, actor, enrollment_id, body):
    row, application = locked_documentation(db, actor, enrollment_id)
    check_documentation_version(row, body.expected_version)
    cohort = db.get(Cohort, row.cohort_id)
    decision = db.scalar(select(SelectionDecision.id).where(
        SelectionDecision.enrollment_id == row.id, SelectionDecision.application_id == row.application_id,
        SelectionDecision.cohort_id == row.cohort_id, SelectionDecision.decision == 'admitida'))
    require_accreditation_eligibility(row, application, cohort, decision is not None)
    if row.documentation_state != 'accredited':
        row.documentation_state = 'accredited'
        row.documentation_version += 1
        row.documentation_accredited_by, row.documentation_accredited_at = actor.user.id, utcnow()
        audit.record(db, actor, 'enrollment.documentation_accredited', 'enrollment', str(row.id),
                     state=row.documentation_state, version=row.documentation_version)
    db.commit()
    return documentation_out(row)


def revoke_documentation(db, actor, enrollment_id, body):
    row, _ = locked_documentation(db, actor, enrollment_id)
    check_documentation_version(row, body.expected_version)
    if row.documentation_state == 'accredited':
        row.documentation_state = 'pending'
        row.documentation_version += 1
        row.documentation_accredited_by, row.documentation_accredited_at = None, None
        audit.record(db, actor, 'enrollment.documentation_revoked', 'enrollment', str(row.id),
                     state=row.documentation_state, version=row.documentation_version)
    # Allow correction of documentary evidence even if academic enrollment is no longer active.
    db.commit()
    return documentation_out(row)


def documentation_history(db, actor, enrollment_id, limit, offset):
    row = readable_enrollment(db, actor, enrollment_id)
    query = select(AuditEvent).where(AuditEvent.target_type == 'enrollment', AuditEvent.target_id == str(row.id),
        AuditEvent.action.in_(('enrollment.documentation_accredited', 'enrollment.documentation_revoked')))
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    events = db.scalars(query.order_by(AuditEvent.at, AuditEvent.id).limit(limit).offset(offset))
    # Only documentary state changes are projected, never audit actors, role strings or arbitrary metadata.
    items = [DocumentationHistoryItem(version=event.meta['version'], state=event.meta['state'], recorded_at=event.at) for event in events]
    audit.record(db, actor, 'enrollment.documentation_history_viewed', 'enrollment', str(row.id))
    db.commit()
    return dict(enrollment_id=row.id, items=items, total=total)
