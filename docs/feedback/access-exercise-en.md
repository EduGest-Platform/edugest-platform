# Synthetic access exercise with a rubric and test-based grading (KAN-152)

Foundation of the automated feedback demo (KAN-67). Everything is **synthetic**: the team wrote the statement, the submissions and the results. It is not a real assessment and validates nothing about people.

## What is where

| Path | Content |
|---|---|
| `evals/feedback/exercise/statement-es.md`, `statement-en.md` | Statement for the applicant: function `resumen_asistencia(estados)` |
| `evals/feedback/exercise/rubric.json` | 4-criterion rubric, weights, levels 1–3 and level rule |
| `evals/feedback/exercise/cases.json` | 10 test cases; each one belongs to exactly one criterion |
| `evals/feedback/reference/solucion.py` | Reference solution |
| `evals/feedback/submissions/` | 4 synthetic submissions with known faults: correct, partial, with errors and hanging |
| `evals/feedback/grade.py` | Grader |
| `evals/feedback/results.json` | Precomputed results for the feedback draft (KAN-191) |
| `evals/feedback/test_feedback_exercise.py` | Tests; they run in the `feedback` CI job |

## Rubric

| Criterion | Weight | How it is measured |
|---|---|---|
| Functional correctness | 40 | 5 test cases |
| Edge cases and input validation | 25 | 5 test cases |
| Readability and structure | 20 | Always the teacher |
| Explanation of decisions | 15 | Always the teacher, on `EXPLICACION.md` |

- **Levels from tests:** 3 if every case of the criterion passes; 2 if at least half pass; 1 if fewer pass. If the submission cannot be imported, the criterion gets **no level** and the submission is **incomplete**: there is never a level 0.
- **Points:** sum of `weight × level / 3`, out of 100. The grader only computes the 65 points of the test-measured criteria; readability and explanation stay without a level and with the teacher review pending.
- **Not exclusionary:** `nota_minima` is `null`. The exercise adds extra points in preselection.
- `competencias` is empty on purpose: competencies C1–C10 belong to enrolled coders, not to applicants.

## Results of the synthetic submissions

| Submission | Correctness | Edge cases | Automatic points (out of 65) |
|---|---|---|---|
| `s1_correcta` | 3 | 3 | 65.0 |
| `s2_parcial` | 3 | 1 | 48.3 |
| `s3_errores` | 1 | 1 | 21.7 |
| `s4_colgada` | 2 | 1 | 35.0 |

## How to run it

From the repository root, with Python 3.12 and no dependencies:

```sh
python evals/feedback/grade.py                   # regenerates results.json (about 10 s)
python evals/feedback/grade.py --check           # fails if results.json is out of date
python -m unittest discover -s evals/feedback -v # the tests, as in CI
```

If you change the statement, the rubric, the cases or a submission, regenerate `results.json` and commit it in the same commit: test 4 fails when it is out of date.

## Guarantees and limits

- **It never runs real applicants' code.** The grader only accepts the folders in `evals/feedback/submissions/`, written by the team. Grading in an isolated sandbox (KAN-172) is out of scope.
- Each case runs in its own process, with isolated Python (`-I`), no bytecode caches (`-B`) and a 2-second limit. A hanging case counts as failed and does not block the rest.
- `results.json` is deterministic: it stores no dates, timings or local paths.
- Test 6 checks that there are no emails, DNI, NIE or phone numbers in `evals/feedback`.
- Teacher criteria are never decided by a test or by AI. The KAN-191 draft may only suggest them, and nothing is published without review (KAN-67).

## What KAN-191 uses

For each submission: `criterios` (level, passed and total per criterion), `puntos_automaticos`, `revision_docente_pendiente` and `casos` (id, criterion, passed and a readable `detalle`, for example `esperado {...}, obtenido {...}` or `tiempo agotado (2 s)`). Plus the `rubrica` id and version, to record which version the draft was generated from.
