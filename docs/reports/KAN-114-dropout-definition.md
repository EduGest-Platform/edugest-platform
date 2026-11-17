# KAN-114 — Dropout target and feature specification

Spanish: [KAN-114-dropout-definition.es.md](KAN-114-dropout-definition.es.md).

- Jira: [KAN-114](https://anasfady87-1789923749606.atlassian.net/browse/KAN-114), parent KAN-65.
- **Deadline: 2026-11-16**, from Jira `duedate`; the description still mentions a proposed 17/11. This document does not change the deadline or claim on-time completion.
- Prepared: 2026-11-17. Owner: Abdur; reviewer: David; schema/acceptance: Elizabeth. No reassignment or approval is implied.
- Status: **PROPOSED** specification; source inspection completed. No trained model, dataset generation or runtime certification.
- Inspected `dev`: `6afd140feb948b570ed710b8a666e84abc58dbed`; foundation reference: `441772b5421a44d9f1733c6a738f4f844aba60b3`.

## 1. Intended decision support

Binary classification of a **human-confirmed voluntary withdrawal within the next 14 calendar days**, conditional on an active enrollment at cutoff `t`. This operational proxy and horizon are proposals for Abdur/Elizabeth, not validated client definitions of every form of dropout. Scores support teacher outreach only: never admissions, exclusion, sanctions or automatic enrollment changes. Target population is enrolled coders, not applicants.

Proposed observation window: `[t - 14 days, t]`, clipped to enrollment start. Run at most weekly per active enrollment. Early weeks remain eligible with exposure and missingness reported; insufficient data means abstention, not low risk. Normalize timestamps to UTC; retain cohort timezone when deriving local teaching dates. Use separate `occurred_at` and `recorded_at`: both must be at or before `t` for features.

## 2. Label and censoring

| Situation | Target |
|---|---|
| Authorized staff confirms voluntary withdrawal at event time in `(t, t + 14 days]`, with auditable reason | `1` |
| Complete follow-up through horizon; no confirmed withdrawal and no competing completion/transfer event | `0` |
| Follow-up incomplete, disputed/missing reason, missing event time, transfer or completion before horizon | `null` (censored/excluded from supervised training) |
| Withdrawal occurred at/before cutoff | Outside active population; no prediction |
| Absence, overdue work, low competency, silence or alert without confirmed withdrawal | Never sufficient to assign `1` |

`Enrollment.estado == 'baja_voluntaria'` is a current-state hint only: it has no withdrawal timestamp/reason history. It cannot establish a future label by itself. Reconstruct state as of cutoff from future audited history, not today's mutable status. Absence of a withdrawal record without complete follow-up does not establish `0`. Late-recorded outcomes may label a historical training snapshot after follow-up; they must never become historical features.

## 3. Feature dictionary and schema alignment

All values are per enrollment and authorized cohort. IDs join records and group splits, never enter the estimator. The planned EDU-02/EDU-04 sources below do not exist in the current backend.

| Feature | Unit / calculation | Source and availability |
|---|---|---|
| `days_since_enrollment` | Elapsed calendar days at cutoff; nonnegative | Enrollment start needs explicit agreement; current `created_at` is record creation, not necessarily course entry |
| `scheduled_day_equivalents` | Sum of held session fractions in window | Planned EDU-02 `AttendanceSession.duration_fraction`; exclude future sessions |
| `unjustified_absence_days` | Sum fractions for confirmed unjustified absences | Planned EDU-02 records; 0.5 half-day, 1 full-day; deduplicate enrollment/session |
| `justified_absence_days` | Separate sum of confirmed justified absences | Planned EDU-02; context for support, never a sanction |
| `attendance_unknown_fraction` | Unrecorded held exposure / held exposure | Planned EDU-02; zero exposure yields null, never zero absence |
| `unjustified_absence_rate` | Unjustified absence days / held day equivalents | Planned EDU-02; null on zero denominator; report missingness alongside rate |
| `absence_rule_signal` | Boolean: at least 3 absences in last 6 registered sessions | Existing local `applyAbsenceRule`; planned server equivalent requires parity tests; pending is excluded, and half-day policy needs agreement |
| `assessed_competency_fraction` | Distinct assessed active competencies / effective active competencies | Planned EDU-04; dynamic bootcamp/cohort catalog, no fixed C1–C10 feature columns; null if denominator zero |
| `mean_competency_level` | Mean latest published level 1–3 per assessed competency as of cutoff | Planned EDU-04 versioned evaluations; no evaluation means null, not level 0; compare only compatible rubric versions |
| `competency_missing_fraction` | Unassessed active competencies / active competencies | Planned EDU-04; report denominator and missingness |

Candidate delivery features are deferred to the Activity/Submission contract; do not invent a database column or infer an overdue submission from missing data. No real names, email, contact data, sensitive attributes, raw notes, future decisions, risk alerts, final status or target-derived values enter model features. Cohort/program IDs remain metadata for scope, evaluation and splits.

Current evidence: `api/app/modules/learning/models.py` has Enrollment with `person_id`, `cohort_id`, `estado`, `created_at`; `api/app/modules/catalog/models.py` has Cohort dates `inicio`/`fin`. `src/gistar/types.ts` and `domain.ts` are local demo semantics, not persisted academic data. Only migration `0001` exists at the inspected base. The legacy rule counts sessions, **not** day-equivalent absences: do not silently replace 3/6 with a different threshold.

## 4. Synthetic evaluation protocol

Abdur owns the subsequent fixed-seed generator, dataset version and model card. Generate longitudinal synthetic events and independent documented latent outcomes; do not define labels directly as the same absence threshold used as a feature. These labels demonstrate a pipeline, not real-world validity or fairness.

Compare `DummyClassifier` with `LogisticRegression`; fit imputation/scaling on training folds only and retain missingness indicators. Keep all snapshots of the same synthetic person in one split, including reenrollments. Use temporal train/validation/test partitions with a horizon gap so training labels cannot observe validation outcomes. Reserve held-out cohorts when enough groups exist; otherwise state the limitation. Publish positive prevalence, support, confusion matrix, precision, recall, F1, PR-AUC and calibration/Brier score when defined; report undefined metrics and one-class folds explicitly. Choose any teacher-alert threshold on validation only and document review capacity; do not use it as a dropout decision. Synthetic subgroup analysis cannot certify fairness.

## 5. Acceptance scenarios for subsequent implementation

1. A 0.5 unjustified absence plus a 1-day absence totals 1.5; justified absence remains separate.
2. A held session without a record is unknown, not present; zero exposure yields null rates.
3. Future events or edits recorded after cutoff do not change that historical feature snapshot.
4. Confirmed withdrawal exactly at horizon is positive; at cutoff it is outside the active population; incomplete follow-up is censored.
5. No same-person snapshots cross splits; training outcomes stop before validation cutoff.
6. No published competency evaluation means missing, not 0; archived/future versions do not contaminate historical catalog state.
7. The 3/6 local rule remains advisory and never supplies the target label or alters enrollment.
8. Authorized teacher can request in-scope risk; another cohort returns 403 in the future API adapter. The model never chooses scope.

These are required future tests, not executed tests in this documentation PR.

## 6. Approval and handoff

| Decision | Accountable person | State |
|---|---|---|
| Voluntary-withdrawal proxy, 14-day horizon/window, weekly cadence and censoring | Abdur + Elizabeth | Pending |
| Enrollment start, withdrawal event history and EDU-02/04 field mapping | Elizabeth, reviewed with Abdur | Pending; blocks DB adapter and reliable labels |
| Missingness/abstention policy, rule parity and threshold for support | Abdur + Elizabeth; Anas for existing-rule semantics | Pending |
| Technical cross-review, leakage/split protocol | David | Pending |

This PR supplies the reviewable definition deliverable. Do not mark KAN-114 Done until cross-review and the decisions above are recorded. No meeting, client acceptance or model performance is fabricated. No Jira changes, migrations or deployment are included.
