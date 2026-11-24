from sqlalchemy import func, select

from app.modules.catalog.models import Call, Program
from app.modules.catalog.publication_policy import require_published
from app.modules.catalog.publication_schemas import PublicCourseOut


def published_courses_query(program_id=None, admission_state=None):
    query = select(Call, Program).join(Program, Program.id == Call.program_id).where(Call.publication_state == 'published')
    if program_id is not None:
        query = query.where(Call.program_id == program_id)
    if admission_state is not None:
        query = query.where(Call.estado == admission_state)
    return query


def course_out(call, program):
    return PublicCourseOut(id=call.id, program_id=call.program_id, program_name=program.nombre,
                           name=call.nombre, opens_on=call.opens_on, closes_on=call.closes_on,
                           capacity=call.plazas, admission_state=call.estado)


def list_courses(db, program_id, admission_state, limit, offset):
    query = published_courses_query(program_id, admission_state)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.execute(query.order_by(Call.opens_on.desc(), Call.id).limit(limit).offset(offset))
    return dict(items=[course_out(call, program) for call, program in rows], total=total)


def get_course(db, course_id):
    # Filter before retrieving: unpublished and nonexistent IDs have the same public error.
    row = db.execute(published_courses_query().where(Call.id == course_id)).first()
    require_published(row[0] if row else None)
    return course_out(*row)
