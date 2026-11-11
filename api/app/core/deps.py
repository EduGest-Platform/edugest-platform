from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.authz import Principal
from app.core.db import get_db, utcnow
from app.core.security import token_hash
from app.modules.identity.models import AuthSession, RoleAssignment, User

bearer = HTTPBearer(auto_error=False, description="Token opaco obtenido en POST /api/v1/auth/login")
DB = Annotated[Session, Depends(get_db)]


def _principal(db: Session, creds: HTTPAuthorizationCredentials | None) -> Principal | None:
    if not creds or creds.scheme.lower() != "bearer":
        return None
    sess = db.scalar(select(AuthSession).where(AuthSession.token_hash == token_hash(creds.credentials)))
    if not sess or sess.revoked_at is not None or sess.expires_at <= utcnow():
        return None
    user = db.get(User, sess.user_id)
    if not user or not user.is_active:
        return None
    assignments = list(db.scalars(select(RoleAssignment).where(RoleAssignment.user_id == user.id, RoleAssignment.revoked_at.is_(None))))
    return Principal(user=user, assignments=assignments)


def optional_principal(db: DB, creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]) -> Principal | None:
    return _principal(db, creds)


def current_principal(db: DB, creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]) -> Principal:
    p = _principal(db, creds)
    if p is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sesión no válida o caducada", headers={"WWW-Authenticate": "Bearer"})
    return p


CurrentPrincipal = Annotated[Principal, Depends(current_principal)]
OptionalPrincipal = Annotated[Principal | None, Depends(optional_principal)]
