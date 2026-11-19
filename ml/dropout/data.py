"""Fixed-seed longitudinal fixtures and as-of features for the proposed KAN-114 protocol."""
import hashlib
import json
import random
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

PROTOCOL = "synthetic-dropout-v1"
FEATURES = (
    "days_since_enrollment", "scheduled_day_equivalents", "unjustified_absence_days", "justified_absence_days",
    "attendance_unknown_fraction", "unjustified_absence_rate", "absence_rule_signal",
    "assessed_competency_fraction", "mean_competency_level", "competency_missing_fraction",
)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


@dataclass(frozen=True)
class Attendance:
    session_id: str
    occurred_at: datetime
    recorded_at: datetime
    fraction: float
    status: str


@dataclass(frozen=True)
class Assessment:
    competency: str
    occurred_at: datetime
    recorded_at: datetime
    level: int
    published: bool = True


@dataclass(frozen=True)
class Case:
    person_id: str
    cohort_id: str
    started_at: datetime
    attendance: tuple[Attendance, ...]
    competencies: tuple[str, ...]
    assessments: tuple[Assessment, ...]
    followup_end: datetime
    withdrawal_at: datetime | None = None
    withdrawal_recorded_at: datetime | None = None
    confirmed: bool = True
    competing_at: datetime | None = None


def features(case, cutoff):
    """No status, labels, IDs, notes or future/late-recorded observations enter the estimator."""
    if cutoff.tzinfo is None:
        raise ValueError("Timezone-aware cutoff required")
    if cutoff < case.started_at:
        raise ValueError("Cutoff precedes enrollment")
    held = {}
    for event in case.attendance:
        if max(case.started_at, cutoff - timedelta(days=14)) <= event.occurred_at <= cutoff:
            held.setdefault(event.session_id, []).append(event)
    events = []
    for revisions in held.values():
        if len({(event.occurred_at, event.fraction) for event in revisions}) != 1:
            raise ValueError("Conflicting session schedule")
        visible = [event for event in revisions if event.recorded_at <= cutoff]
        events.append(max(visible, key=lambda event: event.recorded_at) if visible else min(revisions, key=lambda event: event.recorded_at))
    events.sort(key=lambda event: (event.occurred_at, event.session_id))
    if any(event.fraction not in (0.5, 1.0) or event.status not in {"present", "unjustified", "justified", "unknown"} for event in events):
        raise ValueError("Invalid synthetic attendance")
    known = [event for event in events if event.recorded_at <= cutoff and event.status != "unknown"]
    exposure = sum(event.fraction for event in events)
    unjustified = sum(event.fraction for event in known if event.status == "unjustified")
    justified = sum(event.fraction for event in known if event.status == "justified")
    unknown = exposure - sum(event.fraction for event in known)
    recent = known[-6:]
    # Legacy 3/6 counts sessions. Half-day parity has not been agreed: abstain on that signal.
    rule = None if not recent or any(event.fraction == 0.5 for event in recent) else int(sum(event.status == "unjustified" for event in recent) >= 3)
    latest = {}
    for assessment in sorted(case.assessments, key=lambda item: (item.occurred_at, item.recorded_at)):
        if assessment.competency in case.competencies and assessment.published and assessment.occurred_at <= cutoff and assessment.recorded_at <= cutoff:
            if assessment.level not in (1, 2, 3):
                raise ValueError("Invalid competency level")
            latest[assessment.competency] = assessment.level
    denominator = len(set(case.competencies))
    assessed = len(latest) / denominator if denominator else None
    return dict(zip(FEATURES, (
        (cutoff.date() - case.started_at.date()).days, exposure, unjustified, justified,
        unknown / exposure if exposure else None, unjustified / exposure if exposure else None, rule,
        assessed, sum(latest.values()) / len(latest) if latest else None, 1 - assessed if assessed is not None else None,
    )))


def label(case, cutoff):
    end = cutoff + timedelta(days=14)
    if (case.withdrawal_at is not None and case.withdrawal_at <= cutoff) or (case.competing_at is not None and case.competing_at <= cutoff):
        return None, "outside_population"
    if case.competing_at is not None and case.competing_at <= end:
        return None, "censored"
    if case.withdrawal_at is not None and case.withdrawal_at <= end:
        if case.confirmed and case.withdrawal_recorded_at is not None and case.withdrawal_recorded_at <= case.followup_end:
            return 1, "observed"
        return None, "censored"
    return (0, "observed") if case.followup_end >= end else (None, "censored")


def generate(seed=42, people=300):
    if people < 30:
        raise ValueError("At least 30 synthetic people required")
    rng, rows = random.Random(seed), []
    for index in range(people):
        split = "train" if index < people * 0.6 else "validation" if index < people * 0.8 else "test"
        month = {"train": 1, "validation": 4, "test": 7}[split]
        base = datetime(2026, month, 25, tzinfo=timezone.utc)
        latent = rng.random()  # shared synthetic cause; never a feature or a threshold-derived label
        person, cohort = f"synthetic-person-{index:05d}", f"synthetic-{split}-{index % 3}"
        attendance = []
        for day in range(-14, 8):
            at, draw = base + timedelta(days=day), rng.random()
            state = "unknown" if draw < .1 else "justified" if draw < .2 else "unjustified" if draw < .28 + latent * .35 else "present"
            attendance.append(Attendance(f"session-{day}", at, at + timedelta(days=rng.choice([0, 0, 0, 2])), rng.choice([1.0, 1.0, 0.5]), state))
        codes = tuple(f"competency-{i}" for i in range(rng.randint(3, 10)))
        assessments = tuple(Assessment(code, base - timedelta(days=rng.randint(1, 12)), base - timedelta(days=1),
                                       max(1, min(3, round(3 - 2 * latent + rng.gauss(0, .7))))) for code in codes if rng.random() > .2)
        withdrawal = base + timedelta(days=rng.randint(1, 35)) if rng.random() < .1 + .5 * latent else None
        case = Case(person, cohort, base - timedelta(days=28), tuple(attendance), codes, assessments,
                    base + timedelta(days=35 if rng.random() > .1 else 8), withdrawal,
                    withdrawal + timedelta(days=2) if withdrawal else None,
                    competing_at=base + timedelta(days=10) if rng.random() < .04 else None)
        for offset in (0, 7):
            cutoff = base + timedelta(days=offset)
            target, status = label(case, cutoff)
            rows.append({"person_id": person, "enrollment_id": person + "-enrollment", "cohort_id": cohort,
                         "cutoff": cutoff.isoformat(), "horizon_end": (cutoff + timedelta(days=14)).isoformat(),
                         "split": split, "features": features(case, cutoff), "label": target, "label_status": status})
    return {"protocol": PROTOCOL, "seed": seed, "synthetic_only": True, "rows": rows}


def validate_splits(rows):
    groups = {split: [row for row in rows if row["split"] == split] for split in ("train", "validation", "test")}
    for field in ("person_id", "cohort_id"):
        seen = set()
        for selected in groups.values():
            ids = {row[field] for row in selected}
            if seen & ids:
                raise ValueError("Group leakage between splits")
            seen |= ids
    def instant(value):
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            raise ValueError("Timezone-aware split boundaries required")
        return parsed

    for left, right in (("train", "validation"), ("validation", "test")):
        if not groups[left] or not groups[right] or max(instant(row["horizon_end"]) for row in groups[left]) >= min(instant(row["cutoff"]) for row in groups[right]):
            raise ValueError("Temporal horizon leakage or empty split")
    return groups
