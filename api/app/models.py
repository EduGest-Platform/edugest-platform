"""Import every model so SQLAlchemy metadata (and Alembic) see the full schema."""

from app.modules.admissions.models import Application, ApplicationEvent  # noqa: F401
from app.modules.audit.models import AuditEvent  # noqa: F401
from app.modules.catalog.models import Call, Cohort, Program  # noqa: F401
from app.modules.identity.models import AuthSession, Person, RoleAssignment, User  # noqa: F401
from app.modules.learning.models import Enrollment  # noqa: F401
