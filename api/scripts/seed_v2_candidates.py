"""KAN-173 (seed v2): adds synthetic applications to the shared seed so the platform has at least 100.

Run from api/:  python -m scripts.seed_v2_candidates
Deterministic (fixed seed) and repeatable: it only replaces the entries it generated before
(origen = sintetico_seed_v2) and never touches hand-written ones. Only pre-selection stages are generated:
later stages imply human decisions that must not be invented in bulk.
Synthetic only: invented names and the reserved .test e-mail domain.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

from app.core.config import settings

SEED = 173
TARGET_SUBMITTED = 100  # applications that the API loads (drafts stay in the browser)
ORIGIN = "sintetico_seed_v2"
STAGES = (("enviada", 4), ("requisitos_en_revision", 3), ("convocada", 2))
FIRST_NAMES = (
    "Alex", "Noa", "Dani", "Sam", "Iris", "Leo", "Nora", "Hugo", "Vera", "Teo", "Lía", "Íker", "Abril", "Gael",
    "Aitana", "Bruno", "Carla", "Dario", "Elsa", "Fabio", "Gala", "Iván", "Jara", "Lino", "Mara", "Nilo", "Olga", "Pau",
)
LAST_NAMES = (
    "Arce", "Bravo", "Cano", "Duran", "Esteve", "Ferrer", "Gil", "Herrero", "Ibarra", "Jover", "Lago", "Mora",
    "Nieto", "Olmo", "Pardo", "Quintana", "Rey", "Soler", "Toro", "Valle", "Yuste", "Zamora",
)
MOTIVATIONS = (
    "Quiero reorientar mi carrera hacia la tecnología.",
    "Me interesa aplicar datos e IA en mi sector.",
    "Busco una formación práctica para encontrar empleo.",
    "He aprendido por mi cuenta y quiero consolidarlo.",
    "Quiero automatizar tareas repetitivas en mi trabajo.",
)
AVAILABILITY = ("Mañanas", "Tardes", "Flexible")


def generate(data: dict) -> int:
    """Appends generated applications in place and returns how many were generated."""
    base = [a for a in data["candidaturas"] if a.get("origen") != ORIGIN]
    templates = {a["estado"]: a for a in base}
    missing = [stage for stage, _ in STAGES if stage not in templates]
    if missing:
        raise SystemExit(f"seed.json has no hand-written application to copy for: {', '.join(missing)}")
    rng = random.Random(SEED)
    programs = [p["id"] for p in data["programas"]]
    used_names = {a["nombre_ficticio"] for a in base}
    number = max(int(a["id"].split("-")[1]) for a in base)
    stages, weights = zip(*STAGES)
    submitted = sum(a["estado"] != "borrador" for a in base)
    generated = []
    while submitted + len(generated) < TARGET_SUBMITTED:
        number += 1
        stage = rng.choices(stages, weights)[0]
        item = dict(templates[stage])  # same process fields as a hand-written application in that stage
        item.update(
            id=f"A-{number:03d}", nombre_ficticio=_unique_name(rng, used_names), programa_id=programs[number % len(programs)],
            email_demo=f"aspirante-{number:03d}@example.test", motivacion=rng.choice(MOTIVATIONS),
            disponibilidad=rng.choice(AVAILABILITY), estado=stage, origen=ORIGIN,
        )
        generated.append(item)
    data["candidaturas"] = base + generated
    return len(generated)


def _unique_name(rng: random.Random, used: set[str]) -> str:
    while True:
        name = f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"
        if name not in used:
            used.add(name)
            return name


def main() -> None:
    path = Path(settings.seed_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    count = generate(data)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    submitted = sum(a["estado"] != "borrador" for a in data["candidaturas"])
    print(f"Seed v2: {count} candidaturas generadas · {submitted} enviadas en total · {path}")


if __name__ == "__main__":
    main()
