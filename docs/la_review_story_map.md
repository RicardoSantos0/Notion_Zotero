# Learning-Analytics Review — Story Map (WP5, T6.1)

This story map links every research question and claim to the specific table or
figure that evidences it, with a draft caption and an in-text reference
placeholder. All numbers are produced by the tested package functions and the
notebooks in `notebooks/la_review/`; none are hand-entered.

Corpus: **285 included papers** (PRISMA, Figure 1), spanning four learning-analytics
tasks: performance prediction (PRED), descriptive modelling (DESC), knowledge
tracing (KT), and educational recommender systems (ERS).

---

## RQ1 — What predictive problems and student outcomes does the field address, and how are they framed?

**Claim:** Predictive modelling concentrates on a small set of outcomes (grades,
pass/fail and at-risk status, dropout/retention) defined at the course and
programme scope; finer outcome distinctions are sparse.

**Evidence:**
- **Table III** (`table_3_counts.xlsx`) — the redesigned predictive-problem
  taxonomy: distinct papers per (outcome scope × supervised ML task × target
  construct), with early-actionable and deployed-intervention columns.
  *Draft caption:* "Table III. Decomposition of predictive-modelling
  contributions across outcome scope, supervised ML task, and target construct
  (six display groups; n distinct papers)." [see-table-III]
- **Figure 2** (`figure_2.png`) — learner-representation usage over time, showing
  how the inputs framing these problems have shifted.
  *Draft caption:* "Figure 2. Number of papers using each learner-representation
  category by publication year." [see-figure-2]

---

## RQ2 — What data sources, learner representations, and models are used across the four tasks?

**Claim:** LMS/VLE/MOOC logs and assessment records dominate inputs; model
families differ sharply by task (tree ensembles and linear models for PRED,
deep sequence models for KT, filtering methods for ERS).

**Evidence:**
- **Table II** (`data_source_by_task.xlsx`) — data sources by analytical task
  (distinct papers per source per task).
  *Draft caption:* "Table II. Data sources identified in the reviewed studies by
  analytical task." [see-table-II]
- **Table IV** (`task_synthesis_matrix.xlsx`) — task-level synthesis of purpose,
  data, representations, models, metrics, and actionability gaps.
  *Draft caption:* "Table IV. Task-level synthesis matrix across the four
  learning-analytics tasks." [see-table-IV]
- **Figure 4** (`figure_4.png`) — data-source × task heatmap. [see-figure-4]
- **Figure 7** (`figure_7_model_family.png`) — model family by task
  (model_family coverage 93% of PRED papers).
  *Draft caption:* "Figure 7. Distribution of model families across analytical
  tasks." [see-figure-7]

---

## RQ3 — How mature and actionable are the methods (evaluation, deployment, intervention)?

**Claim:** The field is overwhelmingly retrospective: most studies are
backtested on historical data, very few report real deployment, and fewer still
evaluate an intervention. This is the central actionability gap.

**Evidence:**
- **Table V** (`evaluation_maturity.xlsx`) — distinct papers per task per
  evaluation-maturity level (public benchmark only → backtested → tested with
  new students → deployed → deployed with intervention evaluation).
  *Draft caption:* "Table V. Evaluation maturity by learning-analytics task." [see-table-V]
- **Figure 1** (`figure_1.png`) — PRISMA study-selection flow (442 identified →
  285 included). [see-figure-1]
- **Figure 6** (`figure_6.png`) — actionability/deployment funnel for PRED:
  classified → deployed → deployed-with-intervention.
  *Draft caption:* "Figure 6. Deployment funnel for predictive-modelling papers." [see-figure-6]

---

## Future work

- **LLM overlay.** A small but emerging set of papers use large language models
  as a primary method (`llm_primary` tag in `pred_contribution_rows.csv`). This
  is tracked as an overlay, **not** a fifth core LA task; see the `llm_primary`
  discussion. As LLM adoption grows this overlay warrants a dedicated review.
- **Fairness and ethics (data-contingent, DEGRADED).** The canonical dataset
  contains **no structured fairness/ethics fields** (0% coverage; only 2–9%
  incidental free-text mentions). Per the Phase-0 gate (d-009), fairness/ethics
  is treated as discussion-only here rather than as a quantitative table; a
  reproducible fairness synthesis would require schema extension and re-review.
- **Portability.** Few studies evaluate cross-institution or cross-cohort
  transfer; reported results are mostly within-context.
- **Deployment protocols.** Standardised reporting for deployment and
  intervention evaluation is largely absent (Table V, Figure 6).
- **Human-in-the-loop.** Instructor/advisor-facing actionability and feedback
  loops are rarely described.

---

## Manuscript-ready checklist (d-013)

- [x] Every RQ maps to ≥1 table and ≥1 figure with a draft caption.
- [x] All tables/figures regenerate deterministically from canonical bundles.
- [x] Golden fixtures lock Table II, Table III, and Figure 2.
- [x] Ambiguity audit surfaced (Figure 8 developer dashboard).
- [ ] Final copy-edit of captions against journal style.
- [ ] Cross-check embedded chart values against rendered figures (±5%).
