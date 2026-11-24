from typing import Literal

from fastapi import APIRouter, Query

from app.core.deps import DB
from app.modules.catalog import public_service as service
from app.modules.catalog.publication_schemas import PublicCourseList, PublicCourseOut

router = APIRouter(prefix='/public/courses', tags=['catalog'])


@router.get('', response_model=PublicCourseList, summary='Published course offers, excluding drafts')
def list_courses(db: DB, program_id: str | None = Query(None, min_length=1, max_length=20),
                 admission_state: Literal['abierta', 'cerrada'] | None = None,
                 limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0)):
    return service.list_courses(db, program_id, admission_state, limit, offset)


@router.get('/{course_id}', response_model=PublicCourseOut, responses={404: {'description': 'Published offer not found'}},
            summary='One published offer; drafts and unknown IDs are not found')
def get_course(course_id: str, db: DB):
    return service.get_course(db, course_id)
