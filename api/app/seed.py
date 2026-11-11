"""Loads the synthetic dataset shared with the web prototype (src/gistar/seed.json).

Usage: python -m app.seed [--reset]
Idempotent: skips when programs already exist unless --reset is given.
"""

import json
import sys
from datetime import date
from pathlib import Path

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import SessionLocal
from app.core.security import hash_password
from app.modules.admissions.models import Application, ApplicationEvent
from app.modules.catalog.models import Call, Cohort, Program
from app.modules.identity.models import Person, RoleAssignment, User
from app.modules.learning.models import Enrollment

CALLS = [
    # id, program, nombre, prefix, opens, closes, plazas, estado, cohort fed
    ("CONV-IA-2026B", "P-IA", "Convocatoria IA aplicada · otoño 2026", "IA26B", date(2026, 6, 1), date(2026, 7, 31), 25, "cerrada", "COH-IA"),
    ("CONV-DATA-2026B", "P-DATA", "Convocatoria Data y automatización · otoño 2026", "DA26B", date(2026, 6, 1), date(2026, 7, 31), 25, "cerrada", "COH-DATA"),
    ("CONV-IA-2027A", "P-IA", "Convocatoria IA aplicada · primavera 2027", "IA27A", date(2026, 10, 15), date(2026, 12, 15), 25, "abierta", None),
    ("CONV-DATA-2027A", "P-DATA", "Convocatoria Data y automatización · primavera 2027", "DA27A", date(2026, 10, 15), date(2026, 12, 15), 25, "abierta", None),
]
OPEN_CALL = {"P-IA": "CONV-IA-2027A", "P-DATA": "CONV-DATA-2027A"}

# Synthetic staff accounts: role + scope. Domain .example is reserved and never deliverable.
STAFF = [
    ("admin@gistar.example", "Administración demo", [("admin", "global", None)]),
    ("captacion.ia@gistar.example", "Captación IA (demo)", [("captacion", "program", "P-IA")]),
    ("captacion.data@gistar.example", "Captación Data (demo)", [("captacion", "program", "P-DATA")]),
    ("seleccion.ia@gistar.example", "Selección IA (demo)", [("seleccion", "call", "CONV-IA-2027A")]),
    ("docente@gistar.example", "Docente demo", [("docente", "cohort", "COH-IA"), ("docente", "cohort", "COH-DATA")]),
    ("coordinacion@gistar.example", "Coordinación demo", [("coordinacion", "global", None)]),
]
# Person accounts (lifecycle states, no internal role).
PERSON_USERS = {"A-001": "Aspirante demo", "E-001": "Coder demo"}


def load_seed() -> dict:
    return json.loads(Path(settings.seed_path).read_text(encoding="utf-8"))


def reset(db: Session) -> None:
    tables = ["audit_event", "application_event", "enrollment", "application", "auth_session", "role_assignment", "app_user", "person", "cohort", "call", "program"]
    db.execute(text(f"TRUNCATE {', '.join(tables)} RESTART IDENTITY CASCADE"))
    db.commit()


def seed(db: Session) -> None:
    data = load_seed()
    for p in data["programas"]:
        db.add(Program(id=p["id"], nombre=p["nombre"], descripcion=p.get("descripcion", "")))
    db.flush()
    for cid, prog, nombre, prefix, opens, closes, plazas, estado, _ in CALLS:
        db.add(Call(id=cid, program_id=prog, nombre=nombre, codigo_prefix=prefix, opens_on=opens, closes_on=closes, plazas=plazas, estado=estado))
    db.flush()
    feeds = {c[8]: c[0] for c in CALLS if c[8]}
    for c in data["cohortes"]:
        db.add(Cohort(id=c["id"], program_id=c["programa_id"], call_id=feeds.get(c["id"]), nombre=c["nombre"], inicio=date.fromisoformat(c["inicio"]), fin=date.fromisoformat(c["fin"])))
    db.flush()

    persons: dict[str, Person] = {}
    for a in data["candidaturas"]:
        persons[a["id"]] = Person(display_name=a["nombre_ficticio"], email=a["email_demo"].lower(), legacy_ref=a["id"])
    for c in data["coders"]:
        persons[c["id"]] = Person(display_name=c["nombre_ficticio"], email=c["email_demo"].lower(), legacy_ref=c["id"])
    db.add_all(persons.values())
    db.flush()

    calls = {c.id: c for c in db.scalars(select(Call))}
    for a in data["candidaturas"]:
        if a["estado"] == "borrador":  # drafts live only in the browser; the aspirant applies through the form
            continue
        call = calls[OPEN_CALL[a["programa_id"]]]
        app = Application(
            codigo=f"{call.codigo_prefix}-{call.next_seq:04d}", legacy_ref=a["id"], person_id=persons[a["id"]].id, call_id=call.id, stage=a["estado"],
            motivacion=a["motivacion"], disponibilidad=a.get("disponibilidad") or "Flexible", acepta_datos_sinteticos=True,
        )
        call.next_seq += 1
        db.add(app)
        db.flush()
        db.add(ApplicationEvent(application_id=app.id, tipo="creada", resumen="Candidatura importada del dataset sintético"))
    for c in data["coders"]:
        db.add(Enrollment(person_id=persons[c["id"]].id, cohort_id=c["cohorte_id"], estado="activa"))

    pwd = hash_password(settings.demo_password)
    for email, name, roles in STAFF:
        u = User(email=email, display_name=name, password_hash=pwd)
        db.add(u)
        db.flush()
        for role, st, sid in roles:
            db.add(RoleAssignment(user_id=u.id, role=role, scope_type=st, scope_id=sid))
    for ref, name in PERSON_USERS.items():
        db.add(User(email=persons[ref].email, display_name=name, password_hash=pwd, person_id=persons[ref].id))
    db.commit()


def main() -> None:
    with SessionLocal() as db:
        if "--reset" in sys.argv:
            reset(db)
        elif db.scalar(select(Program.id).limit(1)):
            print("Seed: datos ya presentes, nada que hacer (usa --reset para recargar)")
            return
        seed(db)
        print("Seed: datos sintéticos cargados")


if __name__ == "__main__":
    main()
