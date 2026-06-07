# Baseline Freeze — Pre-Task-Pack Snapshot

**Freeze date:** 2026-06-06
**Milestone:** M0 — Phase-0 Baseline Freeze + Data Audit HARD GATE
**Task:** T0.1
**Purpose:** Preserve the pre-task-pack state of all manuscript analysis outputs and the current manuscript draft so that future regenerated outputs can be compared against this known baseline.

---

## Contents

### Analysis output spreadsheets (9 xlsx files)
Copied from `data/analysis_outputs/` in the target repo on 2026-06-06.

| File | Description |
|---|---|
| `data_source_summary.xlsx` | Summary of data sources used across papers |
| `paper_task_summary_tables.xlsx` | Paper-task assignment summary tables |
| `paper_task_summary_tables_camera_ready.xlsx` | Camera-ready version of paper-task summary tables |
| `pred_analysis.xlsx` | Predictive modelling analysis (pre-redesign) |
| `pred_deployment_quality_control.xlsx` | Deployment / quality-control breakdown for PRED papers |
| `pred_horizon_task_target_table.xlsx` | Original short/long-term horizon x task x target table (the pre-redesign Table 3) |
| `pred_horizon_task_target_table_latest.xlsx` | Latest iteration of pred horizon table |
| `pred_unclassified_horizon_papers.xlsx` | PRED papers that could not be classified by the old horizon heuristic |
| `unique_search_terms.xlsx` | Unique search strings used in the systematic search |

### Manuscript assets
| File | Source | Description |
|---|---|---|
| `Literature Review_Actual Paper2.docx` | `c:/Users/ricar/OneDrive - NOVAIMS/PhD/Publications/Literature Review Paper/Literature Review_Actual Paper2.docx` | The current manuscript Word document at freeze date |
| `manuscript_current.md` | `mas/projects/.../intake/manuscript_current.md` | Markdown conversion of the manuscript, used for intake and spec grounding |

---

## Source paths

- Analysis outputs: `c:/Users/ricar/OneDrive - NOVAIMS/PhD/Publications/Literature Review Paper/Notion_Zotero/data/analysis_outputs/`
- Manuscript docx: `c:/Users/ricar/OneDrive - NOVAIMS/PhD/Publications/Literature Review Paper/Literature Review_Actual Paper2.docx`
- Manuscript md: `mas/projects/notion-zotero/proj-20260605-002-notion-zotero-la-review-task-pack/intake/manuscript_current.md`

---

## Usage

These files are frozen references only. Do not edit them. Future pipeline runs will produce regenerated outputs in `data/analysis_outputs/la_review/`. Compare regenerated outputs against this baseline to verify correctness.

The original Table 3 (`pred_horizon_task_target_table.xlsx` / `pred_horizon_task_target_table_latest.xlsx`) is the primary redesign target for WP2 (T3.x milestone). The current design conflates short/long-term horizon with target variable and prediction timing; the redesigned Table 3 will use a multidimensional taxonomy (8 dimensions).
