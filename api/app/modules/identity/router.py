from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import audit
from app.core.authz import Principal
from app.core.config import settings
from app.core.db import utcnow
from app.core.deps import DB, CurrentPrincipal, bearer
from app.core.security import new_token, token_hash, verify_password
from app.core.text import normalize_email
from app.modules.admissions.models import Application
from app.modules.identity.models import AuthSession, RoleAssignment, User
from app.modules.identity.schemas import EnrollmentOut, LoginIn, LoginOut, MeOut, RoleAssignmentOut
from app.modules.learning.models import Enrollment

router = APIRouter(prefix="/auth", tags=["auth"])


def me_out(db: Session, p: Principal) -> MeOut:
    u = p.user
    apps = list(db.scalars(select(Application.id).where(Application.person_id == u.person_id))) if u.person_id else []
    enr = list(db.scalars(select(Enrollment).where(Enrollment.person_id == u.person_id))) if u.person_id else []
    return MeOut(
        id=u.id,
        display_name=u.display_name,
        email=u.email,
        person_id=u.person_id,
        roles=[RoleAssignmentOut(role=a.role, scope_type=a.scope_type, scope_id=a.scope_id) for a in p.assignments],
        application_ids=apps,
        enrollments=[EnrollmentOut(cohort_id=e.cohort_id, estado=e.estado) for e in enr],
    )


@router.post("/login", response_model=LoginOut, summary="Iniciar sesión con una cuenta sintética de demo")
def login(body: LoginIn, db: DB) -> LoginOut:
    try:
        email = normalize_email(body.email)
    except ValueError:
        email = ""
    user = db.scalar(select(User).where(User.email == email)) if email else None
    if not user or not user.is_active or not verify_password(body.password, user.password_hash):
        audit.record(db, None, "auth.login_failed", "user", None)
        db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenciales no válidas")
    token, digest = new_token()
    expires = utcnow() + timedelta(hours=settings.session_ttl_hours)
    db.add(AuthSession(user_id=user.id, token_hash=digest, expires_at=expires))
    assignments = list(db.scalars(select(RoleAssignment).where(RoleAssignment.user_id == user.id, RoleAssignment.revoked_at.is_(None))))
    p = Principal(user=user, assignments=assignments)
    audit.record(db, p, "auth.login", "user", str(user.id))
    db.commit()
    return LoginOut(access_token=token, expires_at=expires, me=me_out(db, p))


@router.get("/me", response_model=MeOut, summary="Usuario, roles con ámbito y estados de la persona")
def me(p: CurrentPrincipal, db: DB) -> MeOut:
    return me_out(db, p)


@router.post("/logout", status_code=204, summary="Revocar la sesión actual (no afecta a otras sesiones)")
def logout(p: CurrentPrincipal, db: DB, creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]) -> None:
    sess = db.scalar(select(AuthSession).where(AuthSession.token_hash == token_hash(creds.credentials))) if creds else None
    if sess:
        sess.revoked_at = utcnow()
    audit.record(db, p, "auth.logout", "user", str(p.user.id))
    db.commit()
