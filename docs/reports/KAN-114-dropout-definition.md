# KAN-114 — Dropout target and feature specification

Spanish: [KAN-114-dropout-definition.es.md](KAN-114-dropout-definition.es.md).

- Jira: [KAN-114](https://anasfady87-1789923749606.atlassian.net/browse/KAN-114), parent KAN-65.
- **Deadline: 2026-11-16**, from Jira `duedate`; the description still mentions a proposed 17/11. This document does not change the deadline or claim on-time completion.
- Prepared: 2026-11-17. Owner: Abdur; reviewer: David; schema/acceptance: Elizabeth. No reassignment or approval is implied.
- Status: **PROPOSED** target/feature specification. Academic-schema alignment updated 2026-11-20 against dev `5ca5194` (#67/#78/#57 integrated). The synthetic experiment exists separately; this document does not validate a model for people or certify a PostgreSQL-to-ML adapter.
- Original inspection: `6afd140feb948b570ed710b8a666e84abc58dbed`; foundation reference: `441772b5421a44d9f1733c6a738f4f844aba60b3`. Current field mapping below supersedes the old claim that EDU-02/04 tables were absent. No target/horizon/threshold approval is inferred.

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

All values remain per enrollment and authorized cohort. IDs join records and group splits, never enter the estimator. Integrated migration `0008_attendance_and_competencies.py` now supplies EDU-02/04 tables. Mapping is **CODE_PRESENT_NOT_RUN** source inspection, not implementation of historical ML extraction.

| Feature | Integrated source / proposed derivation | Remaining semantic constraint |
|---|---|---|
| `days_since_enrollment` | `Enrollment.created_at` exists; `Cohort.inicio`/`fin` are course dates. | Neither proves a person's effective start. Do not silently use either as ground truth; agree the start definition or keep this feature unavailable. |
| `scheduled_day_equivalents` | `AttendanceSession.cohort_id`, `session_date`, `shift`, `duration_fraction`, `created_at`; sum eligible held fractions, 0.5/1. | Date/shift is not an occurrence timestamp. Define cohort timezone and when a slot counts as completed; exclude sessions created after cutoff and future/uncompleted slots. |
| `unjustified_absence_days` | Join session -> `AttendanceRecord.session_id`/`enrollment_id`; `status=ausente`, `justification=no_justificada`; sum fractions. | Historical state must use eligible `AttendanceRecordRevision` rows at cutoff, not today's current record. |
| `justified_absence_days` | Same join, `status=ausente`, `justification=justificada`; sum separately. | Never merge justified and unjustified absences or use justification text as a feature. |
| `attendance_unknown_fraction` | Held exposure without a visible registered revision / held exposure. | No record at cutoff is unknown, not present or absent. Zero held exposure yields null. `presente` and `retraso` are attended in the current service. |
| `unjustified_absence_rate` | Unjustified day equivalents / held day equivalents. | Define the denominator with the same window/slot rules as unknown exposure; return null on zero. |
| `absence_rule_signal` | Legacy `applyAbsenceRule`: 3 absences among last 6 registered sessions. Existing synthetic ML abstains if those sessions include half days. | Session counts are not day equivalents. Require parity and accepted half-day policy before a DB signal; never derive target labels from this rule. |
| `assessed_competency_fraction` | `CohortCompetencyFramework.framework_id` -> `Competency.framework_id`; distinct assessed competencies / effective catalogue. | Reconstruct the assigned framework at cutoff, not just its current link. Missing/unknown effective assignment means unavailable denominator, not zero. |
| `mean_competency_level` | `CompetencyAssessment.enrollment_id`, `competency_id`, `level`, `assessed_at`; latest eligible assessment per competency, levels 1–3. | Assessments have no per-row published flag or separate occurred/recorded timestamps. Use an accepted cutoff rule and compatible framework versions; do not join future rows or average every revision. |
| `competency_missing_fraction` | Unassessed competencies in the effective framework / catalogue size. | Null when the effective catalogue is unknown/empty. No assessment is missing, never level 0. |

### 3.1 Historical reconstruction and unresolved gaps

- Attendance current records expose `updated_at` and `version`. Their append-only revisions expose `record_id`, `version`, `status`, `modality`, `justification`, `changed_at`; revision 1 is the first registration. For as-of features, consider only revisions recorded by cutoff, then select the last by time/version for each record. A correction after cutoff must not rewrite a prior feature snapshot. `reason`, `changed_by` and free text are never predictors.
- Session `created_at` is schedule-record creation, while `session_date`/`shift` describe teaching slots. Existing attendance summaries report the current view, not an arbitrary historical as-of extraction. They must not be passed to ML as historical features without reconstructing revisions and defining slot completion/timezone.
- Cohort/framework assignment overwrites `CohortCompetencyFramework.framework_id`/`assigned_at` on reassignment. Its audit event records previous/current framework IDs. A future adapter must validate a reconstruction using that evidence and `CompetencyFramework.published_at`; today's assignment alone is insufficient. `estado=archivada` today does not by itself establish whether a framework was effective at an earlier cutoff.
- Assessments are append-only, stamped by the server in `assessed_at`; framework-level publication is distinct from a hypothetical assessment publication time. The synthetic `published` flag in `ml/dropout/data.py` is NOT a column in this schema. Define deterministic tie handling and verify catalogue compatibility rather than copying synthetic-event fields into SQL queries.
- `Enrollment.estado` still has no effective start/withdrawal event timestamp, reason or complete follow-up history. Current state cannot produce future labels. Preselection `retirada_expresa`/`silencio_confirmado` are application decisions, not academic voluntary-withdrawal labels. Do not substitute them.
- Integrated #78 provides synthetic academic demo data and 100 submitted applications. It does not certify chronological completeness, label validity or population size for ML: applicants are not necessarily enrolled coders. The standalone synthetic experiment (#53–#56) remains isolated from PostgreSQL.

Sources: [attendance models](../../api/app/modules/attendance/models.py), [attendance service](../../api/app/modules/attendance/service.py), [competency models](../../api/app/modules/competencies/models.py), [competency service](../../api/app/modules/competencies/service.py), [enrollment](../../api/app/modules/learning/models.py), [academic seed](../../api/app/seed_academic.py), [ML protocol](../../ml/README.md).

Delivery features remain deferred to an accepted Activity/Submission contract. No real names, email, sensitive attributes, raw notes, future decisions, risk alerts, final status or target-derived values enter predictors. Scope/IDs remain metadata. All development/demo data stays synthetic.

## 4. Synthetic evaluation protocol

Abdur owns the ML work. The fixed-seed generator, evaluation, offline scoring/model card and local tracking are already integrated (#53–#56); see [ML documentation](../../ml/README.md). These establish a synthetic demonstration pipeline, not accepted target semantics or a DB feature adapter. Generate longitudinal synthetic events and independent documented latent outcomes; do not define labels directly as the same absence threshold used as a feature. These labels demonstrate a pipeline, not real-world validity or fairness.

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

These remain acceptance criteria for a future PostgreSQL-to-ML adapter. Component attendance/competency and standalone synthetic tests already exist, but this documentation PR does not execute or certify the complete as-of/label flow.

## 6. Approval and handoff

| Decision | Accountable person | State |
|---|---|---|
| Voluntary-withdrawal proxy, 14-day horizon/window, weekly cadence and censoring | Abdur + Elizabeth | Pending |
| Enrollment start, withdrawal history and historical EDU-02/04 extraction | Elizabeth, reviewed with Abdur | Integrated fields mapped above; temporal semantics/reconstruction still pending and block a reliable DB adapter/labels |
| Missingness/abstention policy, rule parity and threshold for support | Abdur + Elizabeth; Anas for existing-rule semantics | Pending |
| Technical cross-review, leakage/split protocol | David | Pending |

This PR supplies the reviewable definition deliverable. Do not mark KAN-114 Done until cross-review and the decisions above are recorded. No meeting, client acceptance or model performance is fabricated. No Jira changes, migrations or deployment are included.

## 7. Mapping validation (2026-11-20)

Checked named ORM fields, source links and migration availability locally; no database connection or data mutation. Current-head CI is recorded in the PR. Target, horizon, observation window, cadence and threshold remain PROPOSED. No ML source, model artifacts, migrations, seed, permissions or Jira assignments changed. Abdur remains task owner; Yohanna prepared this reconciliation at the user's request. Elizabeth reviews data contracts and David reviews leakage/methodology, with Abdur's confirmation of the ML boundary.
