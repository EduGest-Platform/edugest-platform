from app.core.authz import ACADEMIC_AGGREGATE_PERMISSIONS
from app.modules.learning.access import cohort_scope


def require_overview_access(actor, cohort):
    # Require all three existing permissions before querying any metric; do not grant new roles.
    for permission in sorted(ACADEMIC_AGGREGATE_PERMISSIONS):
        actor.require(permission, cohort_scope(cohort))


def visible_has_data(suppressed, has_data):
    # Even record-presence flags are hidden for a suppressed group.
    return None if suppressed else bool(has_data)
