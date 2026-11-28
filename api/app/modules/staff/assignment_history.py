"""Record the end of an assignment consistently across staff and cohort workflows."""

from sqlalchemy import update

from app.core.db import utcnow
from app.modules.staff.models import AccessChangeRequest


def end_assignment(db, assignment):
    if assignment.revoked_at is None:
        assignment.revoked_at = utcnow()
    db.execute(update(AccessChangeRequest).where(
        AccessChangeRequest.applied_assignment_id == assignment.id, AccessChangeRequest.state == 'applied',
    ).values(state='revoked'))
