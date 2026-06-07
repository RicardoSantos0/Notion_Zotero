# Taxonomy Notes — LA Student Success Review

**Review:** Machine Learning to Enhance Student Performance: A Comprehensive Review of Higher Education Applications
**Taxonomy version:** 1.1
**Maintainer:** Ricardo Santos
**Last updated:** 2026-06-07

---

## Purpose

This file captures human-reviewer commentary on systematic ambiguity patterns,
edge cases, and adjudication notes that do not fit the structured override schema.
It supplements `manual_overrides.yaml` (field-level overrides) and
`title_overrides.yaml` (paper-level horizon overrides) with explanatory context.

---

## Systematic Ambiguity Patterns

### 1. Dropout disambiguation

"Dropout" appears in both MOOC and HEI contexts but signals different outcome
scopes:

- **MOOC dropout** → `outcome_scope=course_or_module`. MOOC learners are enrolled
  per course with no degree obligation; "dropout" means not completing the course.
- **HEI dropout** (without explicit course context) → `outcome_scope=program_or_degree`.
  A student dropping out of a university means leaving the degree program.
- **Course withdrawal in HEI** (explicit language like "course withdrawal" or
  "WF grade") → `outcome_scope=course_or_module` even at an HEI.

**Decision rule:** check `context_type` FIRST, then re-examine `outcome_scope`.

### 2. GPA and "academic performance"

- Course GPA or course average → `target_construct=grade_or_score` + `outcome_scope=course_or_module`
- Cumulative GPA (CGPA) → `target_construct=gpa_or_cumulative_performance` + `outcome_scope=term_or_semester` or `program_or_degree`
- "Academic performance" without qualification → use `other_or_unclear` until the
  methods section clarifies the actual variable; do NOT default to grade_or_score.

### 3. "At-risk" as framing vs. target

Almost all "at-risk" papers are actually predicting a primary construct (grade,
pass/fail, dropout) and framing the prediction as risk identification.
Set `risk_framing=yes` and classify `target_construct` to the actual outcome
variable.  Only use `at_risk_or_performance_tier` when the paper's explicit
label IS a risk tier (e.g. "high-risk / medium-risk / low-risk group") with no
underlying continuous or binary variable disclosed.

### 4. Course completion vs. dropout

These are mathematically complementary but may reflect different modeling choices:
- **Completion** (positive framing): `target_construct=completion_or_certification`
- **Dropout** (negative framing): `target_construct=dropout_or_withdrawal`

When a paper models both (e.g. "predict who completes OR drops out"), use TWO
contribution rows with respective target constructs, or use `completion_or_certification`
and flag the row for human review.

### 5. Prediction timing anchoring (d-011)

Papers frequently self-report "early prediction" when features actually come
from the second half of the course.  Always inspect the methods for the actual
feature extraction cutoff (e.g. "first 3 weeks of features" = `early_course`;
"features through week 8 of 10" = `late_course`).

Specific patterns to watch:
- "Before the course starts" (pre-enrollment features) = `before_course_or_at_course_enrolment`
- "Admission data" for a program = `before_program_or_at_admission`
- "End of first semester" in a 4-year program = `program_milestone`

### 6. cv_design and data leakage risk

`random_fold` designs trained on multi-cohort data are susceptible to temporal
leakage (test students from the same semester as training students, but shuffled).
Flag these for the evidence_quality assessment — they may warrant downgrade from
`high` to `medium` if the paper does not control for cohort effects.

`temporal_or_prospective` is the methodologically sound design; prioritise
identifying these papers for the evaluation maturity (Table 5) analysis.

---

## Edge Cases Resolved in Manual Overrides

See `manual_overrides.yaml` for per-contribution override entries.

Patterns that have required multiple adjudications:
- Papers using "success" as the outcome variable in MOOC contexts (usually course
  completion, not program success)
- Papers using "enrollment" as the target (sometimes predicting whether a student
  will enroll in a follow-on course — this is `enrolment_or_course_selection`, not
  program retention)
- Papers with "final grade" in the title but predicting dropout risk in the body

---

## Golden Fixture Refresh Procedure

See the docstring in `tests/test_learning_analytics_taxonomy.py` (top of file)
for the step-by-step procedure when the taxonomy YAML or classifier output changes.
The `taxonomy_version_stamp` in this file and in `manual_overrides.yaml` must
match the `version` field in `learning_analytics_taxonomy.yaml` after any update.
