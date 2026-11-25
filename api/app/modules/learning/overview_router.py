from datetime import date

from fastapi import APIRouter, Path, Query

from app.core.deps import DB, CurrentPrincipal
from app.modules.learning.overview_schemas import CohortProgressOverview
from app.modules.learning.overview_service import progress_overview

router = APIRouter(tags=['learning'])


@router.get('/cohorts/{cohort_id}/progress-overview', response_model=CohortProgressOverview,
            responses={403: {'description': 'Missing cohort aggregate permissions'}, 404: {'description': 'Cohort not found'},
                       422: {'description': 'Invalid attendance period'}},
            summary='Aggregate-only academic overview, never learner-level rows')
def get_progress_overview(p: CurrentPrincipal, db: DB, cohort_id: str = Path(max_length=20),
                          attendance_from: date | None = Query(None, description='Inclusive attendance-only start'),
                          attendance_to: date | None = Query(None, description='Inclusive attendance-only end')):
    return progress_overview(db, p, cohort_id, attendance_from, attendance_to)
