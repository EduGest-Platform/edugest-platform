from app.core import audit
from app.modules.catalog.models import Cohort
from app.modules.learning.documentation_policy import enrollment_not_found, require_documentation_read, require_reader_role
from app.modules.learning.documentation_schemas import DocumentationOut
from app.modules.learning.models import Enrollment


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
