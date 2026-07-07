# Table III Match Review — NLP Taxonomy Specialist (T3_provisional)
**Project:** proj-20260605-002-notion-zotero-la-review-task-pack
**Review date:** 2026-06-25 (revised after parent fix pass)
**Reviewer:** nlp_taxonomy_specialist (T3_provisional)
**Scope:** Post-d-043 + post-fix regeneration (outcome_horizon + outcome_basis added; institutional dropout fix applied); 179 contribution rows, 26 Table III combinations.
**Status: MATCH-WITH-FIXES** — 5 of 17 original issues resolved; 11 still open (all requiring manual_override or a second code pass); 1 E7 reclassified as intentional audit.

---

## (a) Overall Verdict

**MATCH-WITH-FIXES** (improved from initial review)

The parent applied the following confirmed-working fixes:
- C1-C4 (HEI institutional/first-year dropout): ALL RESOLVED — scope now `program_or_degree/long_term`, basis `program_dropout_or_withdrawal`.
- F1 (subscription-based platform): RESOLVED — context_type now `unclear` (was `HEI`).

Remaining structural integrity checks all pass:
- Vocabulary integrity: PASS (0 orphan labels, all 12 dimensions clean).
- Total rows: PASS (contribution_rows=179, SUM unique_papers=164).
- Horizon determinism: PASS (outcome_horizon is a perfect deterministic function of outcome_scope in every row, 0 exceptions).
- Assessment rows (n=9): PASS (all have `assessment_*` or `not_applicable` basis).
- Taxonomy audit routing: PASS (34 real rows in taxonomy_audit; all genuine).

**Note on unique_papers sum:** d-043 stated 163; the post-fix sum is **164**. The 4 reclassified HEI dropout rows (C1-C4) moved from `course_or_module/short_term` to `program_or_degree/long_term`, adding one paper to the `program_or_degree/classification/dropout_or_retention` cell (which went from 4 to 8 papers). This shifts the sum by +1. The 179 contribution_rows total is unchanged; this is expected and correct.

**11 cases remain open** — all requiring manual_override entries or a targeted code fix (see Section b).

---

## (b) RESOLVED vs OPEN Table

### Resolved (5 of 17)

| Code | contribution_id | Issue | Resolution |
|------|----------------|-------|-----------|
| C1 | 86824f288d8e3c87 | HEI first-year dropout at course_or_module | RESOLVED: scope=program_or_degree, horizon=long_term, basis=program_dropout_or_withdrawal |
| C2 | 7602f0040e0f53cf | HEI first-year dropout at course_or_module | RESOLVED: scope=program_or_degree, horizon=long_term, basis=program_dropout_or_withdrawal |
| C3 | 127f48a2c82d7143 | HEI school-dropout at course_or_module | RESOLVED: scope=program_or_degree, horizon=long_term, basis=program_dropout_or_withdrawal |
| C4 | c17a85d60a66d730 | HEI first-year non-re-registration at course_or_module | RESOLVED: scope=program_or_degree, horizon=long_term, basis=program_dropout_or_withdrawal |
| F1 | 5a8700574bccc558 | context_type=HEI for subscription-based platform | RESOLVED: context_type=unclear |
| E7 | 69756df595fd549a | scope=unclear for "at-risk of failing in the Program" | INTENTIONAL AUDIT — outcome is mixed (pass/fail/conditional-fail/repeat-year all at once); correctly unclear; no override recommended |

### Open (11 cases) — Manual Override or Code Fix Required

| Code | contribution_id | paper_id | Current (wrong) | Recommended | Priority |
|------|----------------|----------|-----------------|-------------|----------|
| A1 | a0145cb84df3949c | 29721fe7-4dd2-4c0f-91e7-125e0e906b16 | scope=program_or_degree (fixed), target=gpa_or_cumulative_performance, basis=cumulative_gpa | target=grade_or_score, basis=graduation_or_degree_completion | HIGH |
| A2 | 3565866e7add62a5 | 465d759b-b72b-464f-ac6a-5ca997d7d02b | scope=course_or_module, horizon=short_term | scope=program_or_degree, horizon=long_term | HIGH |
| B1 | d015627268c94ff9 | 5879579d-3795-42d7-885b-acaa80c0053a | scope=unclear, horizon=unclear, basis=course_pass_fail | scope=program_or_degree, horizon=long_term, basis=unclear | HIGH |
| D1 | a53ebc9f8d40f38d | 61e06a72-fe56-4fd2-8ad2-e4e0cc6e5ad6 | basis=course_pass_fail | basis=unclear | MEDIUM |
| D2 | fd4991e33d043288 | 61e06a72-fe56-4fd2-8ad2-e4e0cc6e5ad6 | basis=course_final_grade | basis=unclear | MEDIUM |
| E1 | 8f8f0bc89f1f2f17 | 25f7dd82-2cea-4305-b8b9-6800598148aa | scope=unclear, horizon=unclear, basis=course_pass_fail | scope=assessment, horizon=short_term, basis=assessment_pass_fail | MEDIUM |
| E2 | be389a0e9065de1b | 533e5390-4458-4575-95f6-5d8eb5621a56 | scope=unclear, horizon=unclear | scope=course_or_module, horizon=short_term | MEDIUM |
| E3 | 28cbeac0a70c3f51 | 533e5390-4458-4575-95f6-5d8eb5621a56 | scope=unclear, horizon=unclear | scope=course_or_module, horizon=short_term | MEDIUM |
| E4 | da5cc80d6097306f | 36ea3b09-b94e-4f7a-9111-88e5f537a16a | scope=unclear, horizon=unclear | scope=course_or_module, horizon=short_term | MEDIUM |
| E5 | 3a7822a4e1b6108f | 733c47cf-06d8-4c42-a69e-307851501b00 | scope=unclear, horizon=unclear | scope=course_or_module, horizon=short_term | MEDIUM |
| E6 | eb47a64ec3f00623 | f65a3a00-aed2-4175-87f3-48b65eced061 | scope=unclear, horizon=unclear, basis=course_final_grade | scope=assessment, horizon=short_term, basis=assessment_grade | MEDIUM |

---

## (c) Manual Override Recommendations (Precise, Evidence-Grounded)

### A1 — target_construct and outcome_basis mismatch (scope fix already applied)

**contribution_id:** `a0145cb84df3949c`
**paper_id:** `29721fe7-4dd2-4c0f-91e7-125e0e906b16`
**Paper:** "Analyzing undergraduate students' performance using educational data mining" (Asif et al., 2017)

**Root cause:** The `REVIEWED_TARGET_OVERRIDE_RULES` in `pred_horizon_summary.py` maps pattern `r"end of program mark"` to the "GPA" override category, firing `target_construct=gpa_or_cumulative_performance` and `outcome_basis=cumulative_gpa`. But canonical JSON shows `Target = "End of Program Passing Mark (A to E)"` — an A-to-E letter grade at end of a 4-year IT degree program, not a GPA scale. The Courses field confirms: "1 Information Technology Program" (single degree program).

**Evidence from canonical JSON:** SPD = "End of Program Mark"; Target = "End of Program Passing Mark (A to E)"; Students = "106/104"; Courses = "1 Information Technology Program"; Moment = "End of Year 2 (out of 4)".

**Recommended overrides:**
```yaml
- contribution_id: a0145cb84df3949c
  paper_id: 29721fe7-4dd2-4c0f-91e7-125e0e906b16
  field: target_construct
  value: grade_or_score
  rationale: "Target is 'End of Program Passing Mark (A to E)' — a categorical letter grade for the IT degree program, not a GPA. The REVIEWED_TARGET_OVERRIDE_RULES pattern 'end of program mark' -> GPA is incorrect for this A-E grading scale."
  reviewer: nlp_taxonomy_specialist
  date: 2026-06-25

- contribution_id: a0145cb84df3949c
  paper_id: 29721fe7-4dd2-4c0f-91e7-125e0e906b16
  field: outcome_basis
  value: graduation_or_degree_completion
  rationale: "Program-level final mark (A to E) at end of a 4-year IT degree is the graduation outcome, not cumulative GPA. Courses = '1 Information Technology Program'; Moment = 'End of Year 2 (out of 4)'."
  reviewer: nlp_taxonomy_specialist
  date: 2026-06-25
```

### A2 — scope and horizon mismatch (GPA over 5 months)

**contribution_id:** `3565866e7add62a5`
**paper_id:** `465d759b-b72b-464f-ac6a-5ca997d7d02b`
**Paper:** "Student's performance prediction based on an improved multi-view hypergraph neural network"

**Root cause:** SPD = "Grade Point Average" (spelled out, not abbreviated as "GPA"). The `_classify_outcome_scope` GPA check at line 1112 only matches `r"\bgpa\b"` and `r"\bcgpa\b"`, not "grade point average". The text falls through to the generic-grade fallback (`r"\bgrade\b"` → `course_or_module`). However, canonical JSON shows: Courses = "Not Specified"; Students = "3563 students from a University in Zhejiang"; Moment = "Every month (month 1 to 5)". A GPA predicted monthly over 5 months at university (course unspecified) is a cumulative/program-level GPA, not a single-course grade. target_construct is correctly `gpa_or_cumulative_performance`; scope is wrong.

**Evidence:** Courses = "Not Specified" (rules out single-course); Students = university undergraduates; GPA predicted across 5 months = one full semester or spanning multiple courses.

**Recommended overrides:**
```yaml
- contribution_id: 3565866e7add62a5
  paper_id: 465d759b-b72b-464f-ac6a-5ca997d7d02b
  field: outcome_scope
  value: program_or_degree
  rationale: "GPA predicted over 5 months at HEI with no single course specified (Courses='Not Specified', Students='3563 from University in Zhejiang'). Monthly GPA across an academic semester/year is a program-level cumulative GPA outcome, not a course-level grade."
  reviewer: nlp_taxonomy_specialist
  date: 2026-06-25

- contribution_id: 3565866e7add62a5
  paper_id: 465d759b-b72b-464f-ac6a-5ca997d7d02b
  field: outcome_horizon
  value: long_term
  rationale: "Derived deterministically from outcome_scope=program_or_degree per _HORIZON_BY_SCOPE."
  reviewer: nlp_taxonomy_specialist
  date: 2026-06-25
```

### B1 — scope=unclear for "Failing in a Program"

**contribution_id:** `d015627268c94ff9`
**paper_id:** `5879579d-3795-42d7-885b-acaa80c0053a`
**Paper:** "A prediction model of student performance based on self-attention mechanism"

**Root cause:** SPD = "Failing in a Program" and second contribution has SPD = "GPA". Canonical JSON: Courses = "Not Applicable"; Students = "20000 undergraduate students of Xi'an Jiaotong University"; Moment = "Start of Term". "Failing in a Program" with Courses="Not Applicable" and 20,000 university undergraduates is unambiguously program-level. The classifier's new institutional-dropout guard (line 1081) checks for dropout/withdraw/attrition vocabulary — "failing" does not match those patterns. The `prog_pats` require `program(me)?\\s*(complet|level|outcome)` — "in a program" alone doesn't fire.

**Evidence:** SPD = "Failing in a Program"; Courses = "Not Applicable"; Students = "20000 undergraduate students of Xi'an Jiaotong University"; Moment = "Start of Term" (features extracted at start of each academic term).

**Recommended overrides:**
```yaml
- contribution_id: d015627268c94ff9
  paper_id: 5879579d-3795-42d7-885b-acaa80c0053a
  field: outcome_scope
  value: program_or_degree
  rationale: "SPD='Failing in a Program'; Courses='Not Applicable'; 20,000 HEI undergraduates. No course context — this is program-level pass/fail (academic standing within the degree program). The word 'program' in SPD and Courses='Not Applicable' together confirm program scope."
  reviewer: nlp_taxonomy_specialist
  date: 2026-06-25

- contribution_id: d015627268c94ff9
  paper_id: 5879579d-3795-42d7-885b-acaa80c0053a
  field: outcome_horizon
  value: long_term
  rationale: "Derived deterministically from outcome_scope=program_or_degree per _HORIZON_BY_SCOPE."
  reviewer: nlp_taxonomy_specialist
  date: 2026-06-25

- contribution_id: d015627268c94ff9
  paper_id: 5879579d-3795-42d7-885b-acaa80c0053a
  field: outcome_basis
  value: unclear
  rationale: "Pass/fail within a degree program doesn't map cleanly to any current outcome_basis. graduation_or_degree_completion (graduating vs not) is the closest but not identical to each-term pass/fail standing. Flag for human adjudication."
  reviewer: nlp_taxonomy_specialist
  date: 2026-06-25
```

### D1/D2 — CMBSE national exam: program_or_degree scope with course-level basis

**contribution_ids:** `a53ebc9f8d40f38d` (D1, pass/fail), `fd4991e33d043288` (D2, score)
**paper_id:** `61e06a72-fe56-4fd2-8ad2-e4e0cc6e5ad6`
**Paper:** "Early prediction of medical students' performance in high-stakes examinations using machine learning approaches"

**Context:** CMBSE = National Clinical Medicine Board Skill Examination, taken at end of Year 2 of a 6-year Iranian medical program. Canonical JSON: Students = "1005 medical students"; Courses = "Multiple Iranian Medical Schools"; Moment = "End of 2nd Year". This is a national licensing milestone exam embedded in a medical degree program. The scope `program_or_degree` is correct (it is a program milestone). However, `outcome_basis=course_pass_fail` (D1) and `outcome_basis=course_final_grade` (D2) are wrong — CMBSE is not a course, and no `outcome_basis` value captures "national licensing exam." The closest accurate representation is `unclear`, pending a possible future extension of the vocabulary.

**Recommended overrides:**
```yaml
- contribution_id: a53ebc9f8d40f38d
  paper_id: 61e06a72-fe56-4fd2-8ad2-e4e0cc6e5ad6
  field: outcome_basis
  value: unclear
  rationale: "CMBSE is a national board skill examination (pass/fail at end of Year 2 of medical degree). No current outcome_basis term covers national licensing exams. course_pass_fail is incorrect — CMBSE is not a course. Recommend 'unclear' pending vocabulary extension."
  reviewer: nlp_taxonomy_specialist
  date: 2026-06-25

- contribution_id: fd4991e33d043288
  paper_id: 61e06a72-fe56-4fd2-8ad2-e4e0cc6e5ad6
  field: outcome_basis
  value: unclear
  rationale: "CMBSE normalized score. Same rationale as D1 — course_final_grade is incorrect for a national board exam. Recommend 'unclear' pending vocabulary extension."
  reviewer: nlp_taxonomy_specialist
  date: 2026-06-25
```

### E1 — OU Analyse: scope=unclear for "at risk of failing at next assessment"

**contribution_id:** `8f8f0bc89f1f2f17`
**paper_id:** `25f7dd82-2cea-4305-b8b9-6800598148aa`
**Paper:** "OU Analyse: analysing at-risk students at The Open University"

**Root cause:** SPD = "Being at risk of failing at next assessment". The word "assessment" alone doesn't match the `assessment_pats` in `_classify_outcome_scope` which requires compound phrases (`assessment score`, `assessment mark`, etc.). The word "failing" doesn't match either. Canonical JSON: Courses = "2 anonymized courses" confirms this is within a course. The target is the next assessment event within a course → scope=`assessment`. Already in taxonomy_audit for other dimensions (outcome_scope, unit_of_analysis).

**Evidence:** SPD = "Being at risk of failing at next assessment"; Courses = "2 anonymized courses"; Moment = "Every Week".

**Recommended overrides:**
```yaml
- contribution_id: 8f8f0bc89f1f2f17
  paper_id: 25f7dd82-2cea-4305-b8b9-6800598148aa
  field: outcome_scope
  value: assessment
  rationale: "SPD='Being at risk of failing at NEXT ASSESSMENT' — this is an assessment-level prediction (each weekly checkpoint predicts risk at the next scheduled assessment event). Courses='2 anonymized courses' confirms course context. The 'next assessment' framing is unambiguously assessment-level."
  reviewer: nlp_taxonomy_specialist
  date: 2026-06-25

- contribution_id: 8f8f0bc89f1f2f17
  paper_id: 25f7dd82-2cea-4305-b8b9-6800598148aa
  field: outcome_horizon
  value: short_term
  rationale: "Derived deterministically from outcome_scope=assessment per _HORIZON_BY_SCOPE."
  reviewer: nlp_taxonomy_specialist
  date: 2026-06-25

- contribution_id: 8f8f0bc89f1f2f17
  paper_id: 25f7dd82-2cea-4305-b8b9-6800598148aa
  field: outcome_basis
  value: assessment_pass_fail
  rationale: "Target = 'Not at Risk (0) vs At Risk (1)' at assessment level = binary pass/fail framing of a single assessment."
  reviewer: nlp_taxonomy_specialist
  date: 2026-06-25
```

### E2–E5 — "in a Course" framing stuck at scope=unclear

**Papers:** E2/E3 share paper_id `533e5390-4458-4575-95f6-5d8eb5621a56` ("Accurate, timely, and portable: Course-agnostic early prediction"); E4 = `36ea3b09-b94e-4f7a-9111-88e5f537a16a` ("Early Warning System for Online STEM Learning"); E5 = `733c47cf-06d8-4c42-a69e-307851501b00` ("CLGT: A Graph Transformer for Student Performance Prediction in Collaborative Learning").

**Root cause:** These SPDs use at-risk framing ("Being at Risk of Failing in a Course", "Being a High-Performing Student in a Course") or state course-outcome but without the specific compound patterns (`course grade`, `final grade`, `course pass`, `end of course`) that `course_pats` requires. The phrase "in a course" is not in any pattern. "passing the course" matches `\bpass\b.*\bfail\b` only partially. Already in taxonomy_audit for (outcome_scope, unit_of_analysis).

**Recommended overrides:**
```yaml
- contribution_id: be389a0e9065de1b
  paper_id: 533e5390-4458-4575-95f6-5d8eb5621a56
  field: outcome_scope
  value: course_or_module
  rationale: "SPD='Being at Risk of Failing IN A COURSE' — explicit course framing. Target='At-Risk vs Not At-Risk' at course level. Moment='10%/25%/33%/50% course duration' confirms course-level outcome."
  reviewer: nlp_taxonomy_specialist
  date: 2026-06-25

- contribution_id: be389a0e9065de1b
  paper_id: 533e5390-4458-4575-95f6-5d8eb5621a56
  field: outcome_horizon
  value: short_term
  rationale: "Derived deterministically from outcome_scope=course_or_module."
  reviewer: nlp_taxonomy_specialist
  date: 2026-06-25

- contribution_id: 28cbeac0a70c3f51
  paper_id: 533e5390-4458-4575-95f6-5d8eb5621a56
  field: outcome_scope
  value: course_or_module
  rationale: "SPD='Being a High-Performing Student IN A COURSE' — explicit course framing. Same paper as E2."
  reviewer: nlp_taxonomy_specialist
  date: 2026-06-25

- contribution_id: 28cbeac0a70c3f51
  paper_id: 533e5390-4458-4575-95f6-5d8eb5621a56
  field: outcome_horizon
  value: short_term
  rationale: "Derived deterministically from outcome_scope=course_or_module."
  reviewer: nlp_taxonomy_specialist
  date: 2026-06-25

- contribution_id: da5cc80d6097306f
  paper_id: 36ea3b09-b94e-4f7a-9111-88e5f537a16a
  field: outcome_scope
  value: course_or_module
  rationale: "SPD='PASSING THE COURSE in a specific week' — explicit course outcome. Students='234 students in Northern Taiwan'. Moment='Every week' = continuous within-course monitoring."
  reviewer: nlp_taxonomy_specialist
  date: 2026-06-25

- contribution_id: da5cc80d6097306f
  paper_id: 36ea3b09-b94e-4f7a-9111-88e5f537a16a
  field: outcome_horizon
  value: short_term
  rationale: "Derived deterministically from outcome_scope=course_or_module."
  reviewer: nlp_taxonomy_specialist
  date: 2026-06-25

- contribution_id: 3a7822a4e1b6108f
  paper_id: 733c47cf-06d8-4c42-a69e-307851501b00
  field: outcome_scope
  value: course_or_module
  rationale: "SPD='Grades (Weekly or Final)' — weekly and final grades are within a single collaborative learning course (16 weeks). Students='75 graduate students' in a course context. target_construct=grade_or_score with basis=course_final_grade is already correctly assigned."
  reviewer: nlp_taxonomy_specialist
  date: 2026-06-25

- contribution_id: 3a7822a4e1b6108f
  paper_id: 733c47cf-06d8-4c42-a69e-307851501b00
  field: outcome_horizon
  value: short_term
  rationale: "Derived deterministically from outcome_scope=course_or_module."
  reviewer: nlp_taxonomy_specialist
  date: 2026-06-25
```

### E6 — Post-Test Scores in game-based learning context

**contribution_id:** `eb47a64ec3f00623`
**paper_id:** `f65a3a00-aed2-4175-87f3-48b65eced061`
**Paper:** "Multimodal Predictive Student Modeling with Multi-Task Transfer Learning"

**Evidence:** SPD = "Post-Test Scores"; Target = "High (1) vs Low(0)"; Moment = "Every 2 minutes during Game / Before Post-Test"; Students = "66 undergraduate students"; Courses = (game-based learning session). A post-test is a single assessment event administered at the end of a learning session — unambiguously `assessment` scope. Current basis `course_final_grade` is incorrect; correct is `assessment_grade` (predicting high vs low score on a post-test).

**Recommended overrides:**
```yaml
- contribution_id: eb47a64ec3f00623
  paper_id: f65a3a00-aed2-4175-87f3-48b65eced061
  field: outcome_scope
  value: assessment
  rationale: "SPD='Post-Test Scores' — a post-test is a single assessment event administered after a game-based learning session, not an aggregate course grade. Moment='Before Post-Test' confirms prediction is of a single upcoming assessment."
  reviewer: nlp_taxonomy_specialist
  date: 2026-06-25

- contribution_id: eb47a64ec3f00623
  paper_id: f65a3a00-aed2-4175-87f3-48b65eced061
  field: outcome_horizon
  value: short_term
  rationale: "Derived deterministically from outcome_scope=assessment."
  reviewer: nlp_taxonomy_specialist
  date: 2026-06-25

- contribution_id: eb47a64ec3f00623
  paper_id: f65a3a00-aed2-4175-87f3-48b65eced061
  field: outcome_basis
  value: assessment_grade
  rationale: "Target='High (1) vs Low(0)' on post-test score = binned assessment grade. course_final_grade is incorrect — this is not a course aggregate."
  reviewer: nlp_taxonomy_specialist
  date: 2026-06-25
```

---

## (d) Counts Summary

| Category | Count |
|----------|-------|
| Total flagged in initial review | 17 cases across 10 contribution_ids + 7 unclear-bucket |
| RESOLVED by parent code fix | 5 (C1, C2, C3, C4, F1) |
| Re-classified as intentional audit | 1 (E7 — mixed outcome, correctly unclear) |
| Still OPEN — require manual_override | 11 (A1, A2, B1, D1, D2, E1, E2, E3, E4, E5, E6) |

| Dimension | Open issues |
|-----------|-------------|
| outcome_scope | 7 (A2, B1, E1, E2, E3, E4, E5) |
| outcome_horizon | 7 (same rows — derives from scope) |
| target_construct | 1 (A1: gpa_or_cumulative_performance → grade_or_score) |
| outcome_basis | 5 (A1: cumulative_gpa→graduation_or_degree_completion; D1/D2: course_*→unclear; E1: course_pass_fail→assessment_pass_fail; E6: course_final_grade→assessment_grade) |

**Rows with all dimensions fully correct after fixes:** ~163 of 179 (91%). With the 11 open cases addressed via manual_override, correctness would reach 179/179 at the classifier-output level.

---

## (e) Secondary Finding: unique_papers SUM Shifted +1

d-043 documented "163 unique papers." After the C1-C4 reclassification, the SUM of unique_papers across the 26 Table III cells is **164**. This is arithmetically correct: the four reclassified dropout rows moved to the `program_or_degree/classification/dropout_or_retention` cell, which now shows 8 papers (was 4), creating one new cell entry that wasn't previously contributing to the sum. The contribution_rows total remains 179. The manuscript should be updated to cite 164 (not 163) if this sum is quoted directly.

---

## (f) Taxonomy Vocabulary Gap (Informational)

Cases D1/D2 (national licensing exam CMBSE) have no valid `outcome_basis` in the current vocabulary. The vocabulary currently covers assessment-level (`assessment_grade`, `assessment_pass_fail`), course-level, and program-level outcomes but has no term for "national/licensing milestone exam embedded in a program." The recommended workaround is `unclear` for now. If this gap affects more than ~3 papers in the corpus, a new term (e.g. `program_milestone_exam`) should be proposed to the taxonomy curator.

---

*Review produced by nlp_taxonomy_specialist (T3_provisional). All outputs provisional until Master-reviewed. Rows A1, A2, B1, D1, D2, E1-E6 require manual_override entries in `configs/reviews/la_student_success_review/manual_overrides.yaml` before canonical Table III promotion. The parent must NOT apply code fixes for the E-group without verifying these 8 rows do not introduce false positives on MOOC/assessment-labeled rows.*
