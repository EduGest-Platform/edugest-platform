"""Import every model so SQLAlchemy metadata (and Alembic) see the full schema."""

from app.modules.admissions.models import Application, ApplicationEvent  # noqa: F401
from app.modules.attendance.models import AttendanceRecord, AttendanceRecordRevision, AttendanceSession  # noqa: F401
from app.modules.audit.models import AuditEvent  # noqa: F401
from app.modules.automation.models import AutomationExecution, SimulatedReminder  # noqa: F401
from app.modules.catalog.models import Call, Cohort, Program  # noqa: F401
from app.modules.competencies.models import CohortCompetencyFramework, Competency, CompetencyAssessment, CompetencyFramework  # noqa: F401
from app.modules.identity.models import AuthSession, Person, RoleAssignment, User  # noqa: F401
from app.modules.knowledge.models import KnowledgeChunk, KnowledgeDocument  # noqa: F401
from app.modules.learning.models import Enrollment  # noqa: F401
from app.modules.preselection.models import PreselectionDecision  # noqa: F401
from app.modules.submissions.models import Assignment, Submission  # noqa: F401
from app.modules.requirements.models import CallRequirement, RequirementReview, RequirementReviewRevision  # noqa: F401
from app.modules.selection.models import SelectionApproval, SelectionDecision  # noqa: F401
from app.modules.risk.models import Intervention, RiskAlert  # noqa: F401
from app.modules.staff.models import AccessChangeRequest, Invitation, StaffProfile  # noqa: F401
from app.modules.discussions.models import DiscussionComment, DiscussionThread  # noqa: F401
from app.modules.feedback.models import FeedbackDraft  # noqa: F401
from app.modules.email.models import EmailOutbox  # noqa: F401
