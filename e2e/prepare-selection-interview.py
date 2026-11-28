"""Create an elapsed interview for the disposable selection browser journey."""
import json
import os
from datetime import timedelta
from uuid import uuid4

from sqlalchemy import select

from app import models  # noqa: F401 (register relationship targets)
from app.core.db import SessionLocal, utcnow
from app.modules.admissions.models import Application
from app.modules.catalog.models import Call
from app.modules.identity.models import Person, User
from app.modules.selection.models import SelectionAppointment

if os.environ.get("GISTAR_E2E_FIXTURE") != "disposable-synthetic":
    raise SystemExit("This fixture requires a disposable synthetic database")

with SessionLocal() as db:
    call = db.get(Call, "CONV-IA-2027A")
    selector = db.scalar(select(User).where(User.email == "seleccion.ia@gistar.example"))
    if call is None or selector is None:
        raise SystemExit("Load the synthetic seed before preparing the interview")
    suffix = uuid4().hex[:8]
    person = Person(
        display_name="Entrevista sintética",
        email=f"interview.{suffix}@example.test",
        is_synthetic=True,
    )
    db.add(person)
    db.flush()
    application = Application(
        codigo=f"{call.codigo_prefix}-I{suffix}",
        person_id=person.id,
        call_id=call.id,
        stage="convocada",
        motivacion="Entrevista sintética de prueba.",
        disponibilidad="Flexible",
        acepta_datos_sinteticos=True,
    )
    db.add(application)
    db.flush()
    db.add(SelectionAppointment(
        application_id=application.id,
        kind="individual_interview",
        state="scheduled",
        scheduled_at=utcnow() - timedelta(hours=1),
        location="Sala sintética",
        created_by=selector.id,
    ))
    db.commit()
    print(json.dumps({"id": str(application.id), "code": application.codigo}))
