# Seed v2: synthetic demo data (KAN-173)

Spanish version: [seed-v2-es.md](seed-v2-es.md).

Status: implemented and tested locally. All data is synthetic.

## What it adds

1. **100 submitted applications** in `src/gistar/seed.json` (there were 12). The 88 new ones are generated with a fixed seed (173), so the result is always the same. They only use `@example.test` emails.
2. **Academic data** in the API, derived from `seed.json` with the same rules as the web prototype (`src/gistar/migrate.ts`):
   - One published competency framework per program (P-IA and P-DATA), assigned to its cohort.
   - Competency assessments: the sprint one and the current level stated in `seed.json`.
   - Dated sessions and attendance records for every coder.

`seed.json` is still the single source: the web and the API read the same data.

## How to run it

From `api/`, with the database running and migrated (`alembic upgrade head`):

```bash
python -m app.seed
```

- If the database is empty, it loads the base data and then the academic data.
- If the base data already exists, it only loads the academic data.
- If the academic data already exists (there is a competency framework), it does nothing. So it can run as many times as needed, and staging gets the data without wiping the database.

To regenerate the applications in `seed.json` (only if the generator rules change):

```bash
python -m scripts.seed_v2_candidates
```

It rebuilds the generated applications (marked with `origen: "sintetico_seed_v2"`) and keeps the hand-written ones.

## Academic data rules

| Data | Rule |
|---|---|
| Sprint assessment | COH-IA on 20/10/2026 (IA-01, IA-03, IA-07) and COH-DATA on 27/10/2026 (DAT-02, DAT-03, DAT-07). Level: one below the current one, with a minimum of 1 |
| No sprint assessment | E-019 (did not submit) and E-002, E-006, E-013, E-017 (submission not reviewed) |
| Current level | The one in `seed.json`, dated 30/10/2026. Levels 1 to 3 |
| Sessions | COH-IA: Monday and Thursday, 9:30 to 13:30. COH-DATA: Tuesday and Friday, 15:30 to 19:30. No holidays (12/10, 1/11 and 8/12) |
| Attendance | Half day per session (0.5). Each coder's present and absent counts match their `asistencias_resumen` |
| Absences | Each absence is justified or unjustified. The chance of an unjustified one grows with the latent risk, with the same parameters as the dropout model (`ml/dropout/data.py`) |

Each attendance record stores its first version in the correction history, the same as one created through the API.

## Tests

- `api/tests/test_seed_academic.py`: at least 100 applications with synthetic emails, published and assigned frameworks, levels equal to `seed.json`, attendance that matches the summary, repeatable loading and a reproducible result with the same seed.
- `api/tests/test_rbac.py` and `api/tests/test_applications.py` compute the expected numbers from the seeded data instead of using fixed numbers. So they do not break when `seed.json` changes.

## What it does not do yet

- It does not generate project submissions. They depend on the submissions model (KAN-56).
- It does not change the base data (people, calls, cohorts and users).
