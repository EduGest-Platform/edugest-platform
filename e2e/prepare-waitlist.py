"""Prepare a role-free synthetic applicant for the disposable HTTP waitlist journey."""

import os

from app.core.config import settings
from app.core.db import SessionLocal
from app.core.security import hash_password
from app.modules.identity.models import Person, RoleAssignment, User
from sqlalchemy import select

EMAIL = "f2.waitlist.owner@example.test"
NAME = "Synthetic waitlist applicant"


def main() -> None:
    if settings.environment != "local" or os.environ.get("GISTAR_E2E_FIXTURE") != "disposable-synthetic":
        raise RuntimeError("Disposable local synthetic fixture marker required")
    with SessionLocal() as db:
        # The account is the unique side: several person records may share its email (KAN-274).
        user = db.scalar(select(User).where(User.email == EMAIL))
        if user is None:
            person = Person(email=EMAIL, display_name=NAME, is_synthetic=True)
            db.add(person)
            db.flush()
            db.add(User(
                email=EMAIL, display_name=NAME, person_id=person.id,
                password_hash=hash_password(settings.demo_password),
            ))
        else:
            has_assignment = db.scalar(select(RoleAssignment.id).where(
                RoleAssignment.user_id == user.id, RoleAssignment.revoked_at.is_(None),
            ).limit(1)) is not None
            person = db.get(Person, user.person_id) if user.person_id else None
            if person is None or not person.is_synthetic or not user.is_active or has_assignment:
                raise RuntimeError("The waitlist fixture requires an active role-free applicant")
        db.commit()
    print("Synthetic waitlist applicant ready")


if __name__ == "__main__":
    main()
