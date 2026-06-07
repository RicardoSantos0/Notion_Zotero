# `classify_contribution()` Return-Type Schema
## Status: PROVISIONAL — awaiting Master review before implementation (STEP 1 artifact)
## Version: 1.0 | 2026-06-07 | nlp_taxonomy_specialist (T3_provisional)
## Bound to: learning_analytics_taxonomy.yaml v1.1

---

## 0. Pre-implementation gate notice

Per behavioral_contract.yaml guardrail #5, this schema document must be reviewed and
accepted by the Master orchestrator before any implementation of `classify_contribution()`
is written. This file IS the required artifact. Implementation (STEP 2) does not begin
until explicit Master approval is received.

---

## 1. Function signature

```python
def classify_contribution(row: dict) -> dict:
    ...
```

**Input** (`row: dict`): one row from `pred_contribution_rows.csv`, keyed by column name.
The function reads the following fields from the row (all strings, may be empty):
- `raw_evidence` — pipe-concatenated evidence string (primary text)
- `raw_task` — e.g. "Classification", "Regression", "Clustering"
- `raw_student_performance_definition` — e.g. "Dropout", "GPA at graduation"
- `raw_target` — specific target variable description
- `raw_moment_of_prediction` — feature-extraction timing description
- `raw_context` — educational context field
- `raw_sample_setting` — sample size and setting description
- `raw_models` — comma-separated model names
- `raw_assessment_strategy` — train/test split description
- `paper_title` — for title-override matching (title_overrides.yaml)
- `contribution_id` — stable identifier, used for manual_overrides lookup
- `paper_id` — Zotero page id, used for grouping and override lookup

The function MUST NOT fail silently on missing or empty fields; it degrades gracefully
to `label="unclear"`, `confidence="low"`, `evidence="field absent"` for any missing field.

---

## 2. Exact return type

```python
{
    # Required: one entry per taxonomy dimension
    "supervised_ml_task":   DimensionResult,
    "outcome_scope":        DimensionResult,
    "unit_of_analysis":     DimensionResult,
    "target_construct":     DimensionResult,
    "prediction_timing":    DimensionResult,
    "actionability_status": DimensionResult,
    "risk_framing":         DimensionResult,
    "evidence_quality":     DimensionResult,
    "cv_design":            DimensionResult,
    "context_type":         DimensionResult,

    # Required: top-level routing flag
    "route_to_audit":       bool,   # True if ANY dimension has confidence="low" OR conflict_flag=True

    # Required: override bookkeeping
    "manual_override_applied": bool,  # True if any manual_overrides.yaml entry was applied
}
```

### DimensionResult schema

```python
DimensionResult = {
    "label":         str,   # one controlled-vocab label OR "unclear" (see §3)
    "confidence":    str,   # MUST be one of: "high" | "medium" | "low"
    "evidence":      str,   # non-empty text span or reasoning chain; NEVER empty
    "conflict_flag": bool,  # OPTIONAL key — present and True only when a conflict exists
                            # (do NOT include this key when there is no conflict)
}
```

**Validation rules (enforced at return time, not just on input):**

1. `label` must be a member of the dimension's controlled vocabulary (see §3) or exactly
   the string `"unclear"`. Any other value causes the entire row to be routed to audit.
2. `confidence` must be the Python string literal `"high"`, `"medium"`, or `"low"` —
   no other values permitted. Tests assert `result[dim]["confidence"] in ("high","medium","low")`.
3. `evidence` must be a non-empty string (strip check). If no evidence text is found,
   set `evidence="no supporting text found in available fields"` — do NOT set to empty string.
4. `conflict_flag` is present and `True` only on conflict rows. On non-conflict rows the
   key is absent entirely (do not set to `False`). Tests use `.get("conflict_flag") is True`.
5. `route_to_audit` at the top level is `True` if ANY dimension in the result has
   `confidence == "low"` OR `conflict_flag is True`.

---

## 3. Controlled vocabulary per dimension and reserved "no match" value

The reserved "no match" / unresolved value for ALL dimensions is the string `"unclear"`.
This is used when: (a) the text does not map to any controlled label, (b) evidence is
insufficient, or (c) the classifier abstains. An `"unclear"` label always sets
`confidence="low"`.

| Dimension              | Controlled vocabulary (from taxonomy YAML v1.1)                                                                                                                      | "unclear" permitted? |
|------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------|
| supervised_ml_task     | classification, regression, survival, ranking, sequence_forecast, other                                                                                              | No — use "other"     |
| outcome_scope          | interaction_or_item, assessment, course_or_module, term_or_semester, program_or_degree, institution_or_system, mixed_or_multiple, unclear                            | Yes (in vocab)       |
| unit_of_analysis       | learner_item_interaction, learner_assessment, learner_course, learner_term, learner_program, learner_institution, cohort_or_group, unclear                           | Yes (in vocab)       |
| target_construct       | grade_or_score, pass_fail_or_success_failure, at_risk_or_performance_tier, dropout_or_withdrawal, retention_or_persistence, completion_or_certification, graduation_or_degree_completion, gpa_or_cumulative_performance, next_interaction_correctness, submission_timing_or_delay, learning_gain_or_skill_mastery, enrolment_or_course_selection, time_to_completion, other_or_unclear | Yes ("other_or_unclear" in vocab) |
| prediction_timing      | before_course_or_at_course_enrolment, early_course, mid_course, late_course, end_of_course_or_post_course, before_program_or_at_admission, program_milestone, continuous_or_repeated, unclear | Yes (in vocab)       |
| actionability_status   | retrospective_only, early_backtest_only, tested_on_new_students, deployed_or_deployable, deployed_with_intervention_evaluation, unclear                              | Yes (in vocab)       |
| risk_framing           | yes, no, unclear                                                                                                                                                     | Yes (in vocab)       |
| evidence_quality       | high, medium, low                                                                                                                                                    | No — use "low"       |
| cv_design              | random_fold, temporal_or_prospective, unclear                                                                                                                        | Yes (in vocab)       |
| context_type           | HEI, MOOC, ITS, mixed, unclear                                                                                                                                       | Yes (in vocab)       |

Notes:
- `supervised_ml_task` has no "unclear" in the taxonomy — a clustering study maps to "other".
  The single observed "Clustering" raw_task value maps to "other".
- `evidence_quality` uses the same labels ("high"/"medium"/"low") as the `confidence` field
  but they are INDEPENDENT. evidence_quality is a judgment about the paper's methodology;
  confidence is a judgment about the classifier's certainty.
- `risk_framing` vocabulary literals are `"yes"` and `"no"` (strings, not booleans).

---

## 4. Conflict semantics

A **conflict** arises when a multi-sense term in the input text maps to two or more
controlled-vocab labels on the same dimension with no resolvable disambiguation signal.

### Triggering conditions

A conflict is flagged when ALL of the following hold:
1. Two or more candidate labels are identified for the same dimension.
2. The disambiguation rules in taxonomy YAML §ambiguous-term table do NOT resolve the
   ambiguity (i.e., the disambiguating dimension is itself unclear or contradictory).
3. The margin between candidate scores is below the conflict threshold (implementation:
   cosine-similarity gap < 0.15 for embedding methods, or two regex rules fire simultaneously
   for rule-based methods).

### Conflict output structure

When a conflict is detected on a dimension:

```python
result["target_construct"] = {
    "label":         "unclear",        # never collapse to one label
    "confidence":    "low",            # always "low" on conflict
    "evidence":      "<quoted evidence span showing both senses>",
    "conflict_flag": True,             # key present and True
    # informational: the two conflicting candidates
    # stored in evidence string, e.g.:
    # "CONFLICT: grade_or_score ('Course Grade') vs completion_or_certification ('Completion')"
}
```

The full candidate list is embedded in the `evidence` string as a human-readable CONFLICT
annotation (not a separate key), keeping the DimensionResult schema stable.

### Routing on conflict

Any row where `conflict_flag is True` on ANY dimension:
1. Has `route_to_audit = True` set at the top level.
2. Is written to `taxonomy_audit.csv` by the pipeline.
3. Is NEVER written to the canonical output without a human-approved override entry in
   `manual_overrides.yaml` (audit gate R-017, non-negotiable).

### Golden-case example — "Course Grade or Completion"

```python
input_row = {
    "raw_evidence": "Course Grade or Completion",
    "raw_student_performance_definition": "Course Grade or Completion",
    "raw_target": "Course Grade or Completion",
}
result = classify_contribution(input_row)

# Required outcome (test-R-004-002):
assert result["target_construct"]["confidence"] == "low"
assert result["target_construct"].get("conflict_flag") is True
assert result["route_to_audit"] is True
# evidence string must name both candidates:
assert "grade_or_score" in result["target_construct"]["evidence"] or \
       "CONFLICT" in result["target_construct"]["evidence"]
```

---

## 5. Per-dimension method plan (d-021 discretion)

### Overview table

| Dimension              | Primary method                             | Fallback (if primary fails)           | Full-text required? |
|------------------------|--------------------------------------------|---------------------------------------|---------------------|
| supervised_ml_task     | Deterministic regex + gazetteer            | raw_task field exact match            | No                  |
| outcome_scope          | Hybrid: rules + zero-shot NLI              | Rules only on raw_evidence            | No (but helpful)    |
| unit_of_analysis       | Rules + zero-shot NLI                      | Rules only                            | No                  |
| target_construct       | Hybrid: gazetteer + NLI disambiguation     | Gazetteer only, flag conflicts        | No                  |
| prediction_timing      | Rules on raw_moment_of_prediction (cutoff) | Regex on raw_evidence                 | No                  |
| actionability_status   | Rules + NLI on raw_assessment_strategy     | Rules only                            | Yes (full-text)     |
| risk_framing           | Deterministic regex ("at-risk", "low-performing", etc.) | String match        | No                  |
| evidence_quality       | Heuristic scoring (sample size + assessment strategy) | Conservative default "medium" | Yes (full-text) |
| cv_design              | Deterministic rules on raw_assessment_strategy | Grep full-text (methods section)  | YES — required      |
| context_type           | Deterministic gazetteer on raw_context     | Grep full-text                        | YES — required      |

### Dimension-by-dimension rationale

#### 5.1 `supervised_ml_task` — Deterministic rules + gazetteer
**Method:** Exact-match on `raw_task` field first (the CSV already carries "Classification",
"Regression", "Clustering"). Regex gazetteer on `raw_models` and `raw_evidence` for
survival and sequence_forecast (e.g., "Cox regression", "knowledge tracing", "DKT").

Rationale: The `raw_task` field is already canonically populated by T3.2 with
"Classification" / "Regression" / "Clustering". This is a closed-vocab dimension with
strong lexical signal. Deterministic rules achieve near-perfect precision here.

Confidence assignment:
- "high" when raw_task field is non-empty and unambiguous.
- "medium" when inferred from raw_models (e.g., "survival" inferred from "Cox").
- "low" when raw_task is empty or contradictory.

Anticipated NLP deps: `re` (stdlib) — no external package required for this dimension.

#### 5.2 `outcome_scope` — Hybrid: regex rules + zero-shot NLI
**Method:**

Layer 1 (deterministic, run first):
- Keyword triggers: {"interaction", "item", "question", "response"} -> interaction_or_item
- {"assessment", "assignment", "exam", "quiz", "test score"} -> assessment
- {"course", "module", "MOOC", "semester pass", "course grade"} -> course_or_module (check context)
- {"term", "semester grade", "semester GPA"} -> term_or_semester
- {"graduation", "degree", "program completion", "years to degree", "retention"} -> program_or_degree
- {"institution", "system-level", "school district"} -> institution_or_system

Layer 2 (zero-shot NLI, applied when Layer 1 is ambiguous):
NLI hypothesis template: "The predicted outcome is measured at the [LABEL] level."
Labels tested: all 6 non-unclear vocab terms. Highest entailment score wins if gap > threshold.

Disambiguation rule for MOOC dropout (binding, from taxonomy YAML):
If context_type resolves to MOOC AND outcome text contains "dropout" or "completion"
-> outcome_scope = course_or_module (MOOC dropout rule, always course-level).

Anticipated NLP deps: `re` (stdlib) + `transformers` (zero-shot NLI pipeline).
Zero-shot model: `facebook/bart-large-mnli` (or local cache).

#### 5.3 `unit_of_analysis` — Hybrid: rules + zero-shot NLI
**Method:** The unit of analysis is typically inferable from outcome_scope and context.

Layer 1 (deterministic):
- outcome_scope=interaction_or_item -> unit_of_analysis=learner_item_interaction
- outcome_scope=assessment -> unit_of_analysis=learner_assessment
- outcome_scope=course_or_module -> unit_of_analysis=learner_course (default)
- outcome_scope=term_or_semester -> unit_of_analysis=learner_term
- outcome_scope=program_or_degree -> unit_of_analysis=learner_program
- raw_sample_setting contains "cohort" or "group" -> flag as possible cohort_or_group

Layer 2 (NLI for cohort_or_group disambiguation):
NLI hypothesis: "Each row in the dataset represents a [LABEL]."

Anticipated NLP deps: `re` + `transformers` (shared with outcome_scope).

#### 5.4 `target_construct` — Hybrid: gazetteer (primary) + NLI disambiguation
**Method:** This is the most ambiguous dimension. Multi-stage resolution:

Stage 1 — Gazetteer (high-confidence hits):
A curated regex gazetteer mapping surface forms to labels. Key entries:

```
"next.{0,5}(question|item|attempt).{0,10}correct" -> next_interaction_correctness
"GPA" + program context                            -> gpa_or_cumulative_performance
"dropout|drop.out|withdrawal|attrition"            -> dropout_or_withdrawal
"retention|persistence"                            -> retention_or_persistence
"graduation|degree completion|graduate"            -> graduation_or_degree_completion
"time.to.degree|time.to.completion|years.to.degree"-> time_to_completion
"submission.{0,10}(delay|timing|late)"            -> submission_timing_or_delay
"skill mastery|knowledge state|learning gain"     -> learning_gain_or_skill_mastery
"enroll|course.selection|recommendation"          -> enrolment_or_course_selection
```

Stage 2 — Performance disambiguation (for "performance", "grade", "score", "pass/fail"):
- Continuous score / numeric -> grade_or_score
- Binary pass/fail threshold -> pass_fail_or_success_failure
- Risk tier / category / quantile -> at_risk_or_performance_tier

Stage 3 — Conflict detection (for ambiguous multi-sense terms):
If Stage 1+2 yields two candidate labels for the same row (e.g., "Course Grade or Completion"
-> grade_or_score AND completion_or_certification), emit conflict (§4 above).

Anticipated NLP deps: `re` + `rapidfuzz` (variant spelling) + `transformers` (disambiguation).

#### 5.5 `prediction_timing` — Deterministic rules on feature-extraction cutoff
**Method:** Anchored to the ACTUAL feature-extraction cutoff, not the paper's self-label
(d-011 binding rule). Primary source: `raw_moment_of_prediction`.

Rule table (applied in order, first match wins):

```
"end of course|post.course|after.{0,5}(exam|course)"  -> end_of_course_or_post_course
"end of program|after graduation|post.program"         -> end_of_course_or_post_course
                                                          (with program flag)
"admission|before.{0,5}(enroll|start)|at admission"   -> before_program_or_at_admission
"start of semester|week 1|beginning of course"         -> before_course_or_at_course_enrolment
"week [23]$|first.{0,5}(2|3|4) weeks"                -> early_course
"week [45678]|25%.*course|33%.*course|halfway"         -> mid_course
"week [89]|10|80%|90%|late"                           -> late_course
"every week|continuous|repeated|each.{0,5}(session|week|step)" -> continuous_or_repeated
"end of (first|1st|second|2nd) year|program milestone" -> program_milestone
```

**Anchoring enforcement:** If a paper's `raw_moment_of_prediction` says "End of Course"
but `raw_assessment_strategy` reveals the features are retrospective (all data known),
timing maps to `end_of_course_or_post_course`, not a mid-course label. Self-reported
labels in abstracts are cross-checked against feature timing evidence.

Week 3 of course -> early_course (the golden test case).

Anticipated NLP deps: `re` (stdlib only for this dimension).

#### 5.6 `actionability_status` — Rules + NLI on assessment strategy + full-text
**Method:**

Layer 1 (deterministic on raw_assessment_strategy + raw_evidence):
- "retrospective|historical|past.{0,5}data.only" -> retrospective_only
- "holdout" alone (no temporal signal) -> retrospective_only (with medium confidence)
- "temporal|prospective|new cohort|train.*2019.*test.*2020" -> early_backtest_only or tested_on_new_students
- "deployed|production|live|LMS.{0,20}integrated|implemented" -> deployed_or_deployable
- "intervention.*evaluated|randomized.*trial|A/B.*test" -> deployed_with_intervention_evaluation

Layer 2 (full-text Grep): For borderline cases, Grep the paper full-text for deployment
and validation vocabulary (methods section). This dimension requires the most human
judgment; `"unclear"` is common and legitimate.

Full-text required: Yes (Grep on paper full-text where available).
Anticipated NLP deps: `re` + `transformers` (zero-shot NLI for borderline cases).
Confidence default: many rows will land on `"medium"` or `"low"` due to insufficient detail.

**Risk flag (escalation trigger):** This dimension is the most likely to produce >50
low-confidence rows given that actionability is under-reported in abstracts. If the
proportion of `"unclear"` labels exceeds 40% of rows, escalate to Master for guidance
on whether to default all unclear rows to "retrospective_only" pending full-text review.

#### 5.7 `risk_framing` — Deterministic regex (high precision, closed signal)
**Method:** Regex gazetteer on `raw_student_performance_definition`, `raw_target`,
and `raw_evidence`.

Trigger patterns for `"yes"`:
```
"at.risk|low.performing|bottom.{0,10}(percentile|quartile|group)"
"risk.of.fail|failure.risk|risk.label|risk.score|risk.flag"
"at risk of|identified as at.risk"
"performance.tier|performance.group|performance.cluster"
```

If none fire: `"no"` (with `"high"` confidence if gazetteer coverage is comprehensive).
If signal is present but weak (one mention in context that may be incidental): `"unclear"`.

Important: "at-risk" in the raw text sets `risk_framing="yes"` AND informs
`target_construct` disambiguation (at_risk or pass_fail, not the at_risk_or_performance_tier
label itself for target_construct unless the tier is truly the outcome).

Anticipated NLP deps: `re` (stdlib only for this dimension).

#### 5.8 `evidence_quality` — Heuristic scoring + full-text judgment
**Method:** This is a methodological judgment combining multiple signals.

Scoring inputs:
1. Sample size (from `raw_sample_setting`): parse numeric value.
   - > 1000 students: +2 points
   - 100-1000: +1 point
   - < 100: 0 points
2. Assessment strategy (from `raw_assessment_strategy`):
   - Temporal/prospective validation: +2 points
   - k-fold CV or holdout: +1 point
   - None/No Assessment Strategy: 0 points
3. Replication signal (from `raw_evidence` or title): public dataset / replication: +1 point
4. Model count (from `raw_models`): multiple baselines compared: +1 point

Score -> label mapping:
- 5-6 points: "high"
- 3-4 points: "medium"
- 0-2 points: "low"

Full-text Grep is used when the paper title signals a public dataset (e.g., Open University,
OULAD, ASSISTments) to add the replication point.

Anticipated NLP deps: `re` (for numeric extraction). Possibly `transformers` for the
replication signal if Grep is unavailable.

#### 5.9 `cv_design` — Deterministic rules on raw_assessment_strategy (FULL-TEXT REQUIRED)
**Method:** Primary signal: `raw_assessment_strategy` field. Full-text Grep required
for confirmation (guardrail 8 — cv_design cannot be classified from abstract/title alone).

Rule table:
```
"temporal|prospective|train.*20[0-9]{2}.*test.*20[0-9]{2}|leave.last.semester"
  -> temporal_or_prospective

"k.fold|cross.validation|stratified|repeated.*holdout|leave.one.out"
  -> random_fold  (IF no temporal ordering signal present)

"holdout" alone without temporal context
  -> random_fold (medium confidence, pending full-text confirmation)

"none|no assessment|unspecified|not specified"
  -> unclear
```

Full-text Grep strategy: Search paper PDF-extracted text (if available) for the methods
section keywords: "temporal split", "leave-one-semester-out", "chronological", "train on
[year] test on [year]". A random_fold match from the raw_assessment_strategy field is
upgraded to `"high"` confidence only after full-text confirmation.

Anticipated NLP deps: `re` + `Grep` tool (full-text search). No neural model needed
for this dimension — the signal is highly lexical.

Observed distribution in CSV (N=179):
- "10-Fold Cross-Validation" variants: ~60 rows -> random_fold
- "Holdout Method" variants: ~60 rows -> random_fold (no temporal order confirmed)
- "Temporal Validation": 4 rows -> temporal_or_prospective
- "None"/"None Specified": ~12 rows -> unclear

Expected low-confidence rows on this dimension: ~15-20 (Holdout without temporal
confirmation). This is within the 50-row escalation threshold.

#### 5.10 `context_type` — Deterministic gazetteer + full-text Grep (REQUIRED)
**Method:** Primary: `raw_context` field gazetteer. Full-text Grep required for
confirmation (guardrail 8).

Gazetteer rules:
```
"MOOC|edX|Coursera|FutureLearn|Udemy|open.enrollment|massive.open"  -> MOOC
"Intelligent Tutoring|ASSISTments|Khan Academy|ITS|tutoring.system" -> ITS
"Higher Education|university|college|undergraduate|HEI|degree.program" -> HEI
"Subscription.Based Platform"                                          -> unclear (not in vocab;
                                                                          map to MOOC or ITS
                                                                          pending full-text)
```

Full-text Grep strategy: For rows where raw_context is ambiguous or maps to "unclear",
Grep full-text for platform names and institutional markers.

Observed distribution in CSV (N=179):
- "Higher Education": 162 rows -> HEI (deterministic, high confidence)
- "MOOC": 12 rows -> MOOC
- "Higher Education Students": 1 -> HEI
- "Intelligent Tutoring System": 1 -> ITS
- "Subscription-Based Platform": 1 -> unclear (requires full-text to resolve to MOOC/ITS)
- "Undergraduate course": 1 -> HEI
- "Social Networks in Higher Education": 1 -> HEI (with medium confidence)

Expected low-confidence rows: ~3-5. Well within thresholds.
MOOC disambiguation rule (binding): when context_type=MOOC, outcome_scope=course_or_module
for dropout/completion outcomes (taxonomy YAML §disambiguation.dropout_context_rule).

Anticipated NLP deps: `re` + `Grep` tool.

---

## 6. `taxonomy_audit.csv` column schema

Every row routed to audit (conflict_flag=True OR any dimension confidence="low") is
written to this file. The column schema is:

| Column                    | Type    | Description                                                                                         |
|---------------------------|---------|-----------------------------------------------------------------------------------------------------|
| `contribution_id`         | str     | Stable ID from pred_contribution_rows.csv                                                           |
| `paper_id`                | str     | Zotero page ID                                                                                      |
| `paper_title`             | str     | Paper title (for human readability)                                                                 |
| `audit_reason`            | str     | Comma-separated list of reasons: "low_confidence:<dim>", "conflict:<dim>", "unclear_label:<dim>"   |
| `flagged_dimensions`      | str     | Comma-separated dimension names that triggered the audit route                                      |
| `raw_evidence`            | str     | Original raw_evidence from the input row                                                            |
| `dim_label_<N>`           | str     | For each flagged dimension N: the label assigned (or "unclear")                                     |
| `dim_confidence_<N>`      | str     | For each flagged dimension N: "high"/"medium"/"low"                                                 |
| `dim_evidence_<N>`        | str     | For each flagged dimension N: the evidence string (including CONFLICT annotation if applicable)     |
| `dim_conflict_flag_<N>`   | bool    | For each flagged dimension N: True if conflict, absent otherwise                                    |
| `human_adjudication`      | str     | Empty on write; filled by human reviewer with corrected label                                       |
| `adjudication_status`     | str     | "pending" on write; updated to "approved"/"rejected" by human reviewer                             |
| `routed_at`               | str     | ISO 8601 timestamp of routing                                                                       |

Implementation note: rather than dynamic `dim_label_<N>` columns (which vary by row),
the preferred implementation stores all 10 dimension results as a JSON blob in a single
`dimension_results` column alongside a `flagged_dimensions` column listing which dims
triggered the route. This keeps the schema stable at a fixed column count.

### Preferred fixed-column audit schema

| Column                | Type | Description                                                           |
|-----------------------|------|-----------------------------------------------------------------------|
| `contribution_id`     | str  | Stable ID                                                             |
| `paper_id`            | str  | Zotero page ID                                                        |
| `paper_title`         | str  | Paper title                                                           |
| `audit_reason`        | str  | Human-readable summary of why the row was routed                      |
| `flagged_dimensions`  | str  | JSON array of dimension names with low confidence or conflict         |
| `dimension_results`   | str  | JSON blob of the full classify_contribution() return dict             |
| `raw_evidence`        | str  | Verbatim raw_evidence field                                           |
| `human_adjudication`  | str  | Initially empty; reviewer fills in corrected label per dimension      |
| `adjudication_status` | str  | "pending" / "approved" / "rejected"                                   |
| `routed_at`           | str  | ISO 8601 timestamp                                                    |

---

## 7. Manual overrides interaction

### Precedence rule

Manual overrides ALWAYS take precedence over classifier output. The override application
order is:

```
1. classify_contribution(row) runs -> produces raw_result dict
2. apply_title_overrides(row, raw_result) checks title_overrides.yaml patterns
   against row["paper_title"] (case-insensitive regex search);
   if matched: overrides prediction_timing label and sets confidence="high",
   evidence="title_override: <pattern>"
3. apply_manual_overrides(row, raw_result) checks manual_overrides.yaml for any
   entry where contribution_id matches AND field matches a taxonomy dimension;
   if matched: overrides that dimension's label, sets confidence="high",
   evidence="manual_override: <rationale text>", manual_override_applied=True
4. Re-evaluate route_to_audit after overrides (an override may resolve a conflict
   and remove the audit flag; or may be applied to a non-conflict row)
```

### `manual_override_applied` flag

- Set to `True` on the top-level return dict if ANY override from either file was applied.
- Set to `False` (or absent) if no override applied.
- A row that receives a manual override and has its conflict resolved is still logged
  in the audit trail with `adjudication_status="approved"` — overrides do not suppress
  the audit record, they resolve it.

### Override conflict detection (escalation trigger)

If the override value in `manual_overrides.yaml` is NOT in the controlled vocabulary for
that dimension (e.g., a typo), the pipeline raises a `ValueError` and escalates to Master.
The >5% override conflict escalation trigger (behavioral_contract.yaml) applies to cases
where overrides contradict the automated label on >5% of rows — this is logged and
reported in the pipeline output but does not halt execution.

---

## 8. Disambiguation anchors mapped to expected outputs

The following table maps each spec-defined disambiguation anchor to its expected
`classify_contribution()` output. These confirm consistency with the golden tests
(test-R-004-001 and test-R-004-002).

### Anchor 1: "dropout from a MOOC" (test-R-004-001, tc-001)

Input row fields:
- `raw_evidence`: "dropout from a MOOC predicted at week 3"
- `raw_student_performance_definition`: "dropout from a MOOC"
- `raw_moment_of_prediction`: "week 3"
- `raw_context`: "MOOC"

Expected output:

```python
{
    "outcome_scope":      {"label": "course_or_module",     "confidence": "high", "evidence": "MOOC dropout disambiguation rule: context_type=MOOC => outcome_scope=course_or_module"},
    "target_construct":   {"label": "dropout_or_withdrawal", "confidence": "high", "evidence": "dropout from a MOOC"},
    "context_type":       {"label": "MOOC",                  "confidence": "high", "evidence": "raw_context='MOOC'"},
    "prediction_timing":  {"label": "early_course",          "confidence": "high", "evidence": "week 3 of course => early_course (feature-extraction cutoff rule, d-011)"},
    "route_to_audit":     False,
    "manual_override_applied": False,
}
```

Test assertions satisfied:
- `result["outcome_scope"]["label"] == "course_or_module"` YES
- `result["target_construct"]["label"] == "dropout_or_withdrawal"` YES
- `result["context_type"]["label"] == "MOOC"` YES
- `result["prediction_timing"]["label"] == "early_course"` YES
- All `confidence in ("high","medium","low")` YES

### Anchor 2: "GPA at graduation" (test-R-004-001, tc-002)

Input row fields:
- `raw_evidence`: "GPA at graduation"
- `raw_student_performance_definition`: "GPA"
- `raw_moment_of_prediction`: "end of program"

Expected output:

```python
{
    "outcome_scope":    {"label": "program_or_degree",            "confidence": "high", "evidence": "'at graduation' -> program_or_degree (GPA disambiguation: graduation = program_or_degree)"},
    "target_construct": {"label": "gpa_or_cumulative_performance", "confidence": "high", "evidence": "'GPA at graduation' -> gpa_or_cumulative_performance (GPA gazetteer match)"},
    "route_to_audit":   False,
}
```

Reasoning chain: "GPA" fires the GPA gazetteer. "at graduation" contextualizes it to
program_or_degree (not term_or_semester). No conflict. Both labels are unambiguous.

### Anchor 3: "next question correctness" (test-R-004-001, tc-003)

Input row fields:
- `raw_evidence`: "next question correctness in ITS"
- `raw_student_performance_definition`: "next question correctness"

Expected output:

```python
{
    "outcome_scope":    {"label": "interaction_or_item",      "confidence": "high", "evidence": "next question correctness -> interaction_or_item (item-level outcome)"},
    "target_construct": {"label": "next_interaction_correctness", "confidence": "high", "evidence": "next.{0,5}question.{0,10}correct gazetteer match"},
    "context_type":     {"label": "ITS",                      "confidence": "high", "evidence": "raw_evidence contains 'ITS'"},
    "route_to_audit":   False,
}
```

### Anchor 4: "Course Grade or Completion" (test-R-004-002)

Input row fields:
- `raw_evidence`: "Course Grade or Completion"
- `raw_student_performance_definition`: "Course Grade or Completion"
- `raw_target`: "Course Grade or Completion"

Expected output:

```python
{
    "target_construct": {
        "label":         "unclear",
        "confidence":    "low",
        "evidence":      "CONFLICT: grade_or_score ('Course Grade') vs completion_or_certification ('Completion') — two target_construct candidates with no disambiguating signal; routed to audit",
        "conflict_flag": True,
    },
    "route_to_audit": True,
}
```

Test assertions satisfied:
- `result["target_construct"]["confidence"] == "low"` YES
- `result["target_construct"].get("conflict_flag") is True` YES
- Row written to `taxonomy_audit.csv` YES

### Anchor 5: prediction_timing anchored to feature-extraction cutoff (test-R-004-002, tc-005 / vp-003)

If a paper self-labels as "long-term prediction" but `raw_moment_of_prediction` is "week 3
of course", the expected output is `prediction_timing="early_course"` — matching the
ACTUAL feature cutoff. The paper's self-reported horizon label is ignored in favour of
the cutoff evidence.

### Anchor 6: "at-risk" — risk_framing=yes, NOT primary target_construct

If `raw_student_performance_definition` = "At-risk of Failing in the Program":
- `risk_framing.label = "yes"` (HIGH confidence, gazetteer match "at.risk")
- `target_construct.label = "pass_fail_or_success_failure"` (inferred from "Failing")
- NOT `target_construct.label = "at_risk_or_performance_tier"` unless the outcome
  variable is literally a risk score/tier (not a binary pass/fail).

---

## 9. Anticipated NLP dependencies

The following packages are anticipated. No installation occurs in STEP 1.
Per d-014, all installs are gated on the OneDrive venv-path check in STEP 2.

| Package               | Purpose                                                       | Required?     |
|-----------------------|---------------------------------------------------------------|---------------|
| `re` (stdlib)         | All rule-based dimensions                                     | Always        |
| `spacy` + `en_core_web_sm` | PhraseMatcher for gazetteer; token-level rules         | Preferred     |
| `rapidfuzz`           | Fuzzy variant matching for target_construct gazetteer         | Preferred     |
| `scikit-learn`        | TF-IDF baseline; cosine similarity for conflict threshold     | If NLI unavail|
| `transformers`        | Zero-shot NLI pipeline (`facebook/bart-large-mnli`)           | For ambiguous dims |
| `sentence-transformers` | SBERT kNN for outcome_scope / unit_of_analysis if NLI slow  | Optional      |
| `torch` (CPU wheel)   | Backend for transformers                                      | If transformers used |
| `tokenizers`          | Transitive dep of transformers; pin for reproducibility       | If transformers used |

Stdlib fallback is available for all dimensions via `re` + `difflib`. The classifier
remains functional without any external NLP package (with degraded accuracy on
ambiguous dims). All fallbacks are logged.

---

## 10. Completeness check against verification_plan.yaml

| Verification step | Addressed in schema? | Where                          |
|-------------------|---------------------|--------------------------------|
| vp-001: Schema exists before impl | YES — this document | §0 pre-impl gate notice |
| vp-002: Golden fixtures (tc-001..004) | YES | §8 disambiguation anchors |
| vp-003: Prediction timing cutoff | YES | §5.5 + §8 anchor 5 |
| vp-004: requirements-nlp-lock.txt | Noted | §9 (to be created in STEP 2) |
| vp-005: model_card.yaml | Noted | No model trained in rule-based path; card needed only if NLI/SBERT fit in STEP 2 |
| vp-006: Audit routing | YES | §4 conflict semantics + §6 audit schema |
| vp-007: Tool contract | YES | Only allowed tools used in STEP 1 |
| vp-008: Governance compliance | YES | No roster/governance writes |
| vp-009: Human review gate | PENDING | This document awaits Master review |

---

## 11. Escalation flags pre-identified

1. **actionability_status — likely >50 low-confidence rows**: This dimension is
   under-reported in abstracts. If >40% of rows yield "unclear", escalate to Master
   for a default policy before STEP 2 implementation. Noted in §5.6.

2. **cv_design — Holdout without temporal confirmation**: ~60 rows have "Holdout Method"
   without temporal context. These will be classified as `random_fold` with `"medium"`
   confidence pending full-text Grep. This is within the 50-row threshold but worth
   monitoring.

3. **target_construct — polysemous performance terms**: "performance", "success", "grade",
   "completion" each map to multiple labels. The gazetteer + conflict-detection design
   handles this, but a high conflict rate here (>10 rows) should be expected and reviewed.

4. **No held-out human-coded sample yet**: The 30-paper minimum for Cohen's kappa
   validation (guardrail 6) does not exist yet. If the rule-based path is used without
   any ML model, model_card.yaml is not required. If zero-shot NLI is used, the NLI
   model is pretrained and not fitted on this corpus, so model_card.yaml is simplified.
   Holdout validation is still required before canonical Table III promotion — the human
   review gate (R-017) serves this function pending a formal IRR study.

---

*End of schema artifact. Awaiting Master review before STEP 2 implementation begins.*
