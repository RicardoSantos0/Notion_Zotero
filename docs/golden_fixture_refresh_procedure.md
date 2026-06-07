# Golden Fixture Refresh Procedure (d-013)

This document describes when and how to update the golden fixture CSV files stored in
`tests/fixtures/`.  These fixtures are snapshot baselines for deterministic-regeneration
tests.  A change to a fixture must be deliberate and traceable to a taxonomy or data
change.

---

## When to refresh

Refresh a golden fixture when:

1. The taxonomy YAML (`learning_analytics_taxonomy.yaml`) is updated — e.g., a new
   vocabulary term is added or a label is renamed.
2. A manual override in `manual_overrides.yaml` is added, removed, or changed.
3. The canonical dataset (`data/pulled/notion/learning_analytics_review/`) is re-pulled
   from Notion and the record count changes.
4. A bug fix in the classifier logic causes counts to shift and the new counts are
   verified correct by the author.

**Do NOT refresh** to make a failing test pass without understanding why the counts
changed.  If you do not know why the count changed, investigate first.

---

## Fixtures and their source pipelines

| Fixture file | Source pipeline | Tolerance |
|---|---|---|
| `tests/fixtures/la_table_3_counts.csv` | `pred-problem-table` CLI (T3.4) | +-2 papers |
| `tests/fixtures/la_data_source_counts.csv` | `generate_table2()` in paper_tables.py (T4.1) | exact |
| `tests/fixtures/representation_usage_over_time.csv` | Figure 2 builder in visualization.py (T5.1) | 5% per year-bucket |

---

## Refresh steps

### Step 1 — Verify the canonical data is current

```
# Check when the canonical JSONs were last pulled
ls -lt data/pulled/notion/learning_analytics_review/ | head -5
```

If a fresh pull is needed, run the Notion sync CLI (requires API credentials):

```
notion-zotero sync --dry-run   # preview changes first
notion-zotero sync              # pull latest
```

### Step 2 — Run the generator pipeline (NOT chained with pytest)

Run each generator step **separately** (d-013: no chained `&&` with pytest):

```
# Table 3
python -m notion_zotero.analysis.pred_horizon_summary --output-dir data/analysis_outputs/la_review/tables

# Table 2
python -c "from notion_zotero.analysis.paper_tables import generate_table2; generate_table2('data/pulled/notion/learning_analytics_review')"

# Figure 2 data
python -c "from notion_zotero.analysis.visualization import build_figure_data; build_figure_data()"
```

Alternatively, run the corresponding notebook cell in `notebooks/la_review/01_data_audit.ipynb`
or `02_task_tables_and_table3.ipynb`.

### Step 3 — Review the diff

```
git diff data/analysis_outputs/la_review/
```

Verify that:
- Count changes are consistent with the taxonomy or data change that triggered the refresh.
- No unexpected rows have disappeared or appeared.
- The `taxonomy_version_stamp` in `manual_overrides.yaml` matches the taxonomy YAML `version`.

### Step 4 — Copy outputs to tests/fixtures/

```
# Table 3 counts
cp data/analysis_outputs/la_review/tables/table_3_counts.csv tests/fixtures/la_table_3_counts.csv

# Table 2 data source counts
cp data/analysis_outputs/la_review/tables/data_source_by_task.csv tests/fixtures/la_data_source_counts.csv

# Figure 2 yearly data
cp data/analysis_outputs/la_review/figure_data/representation_usage_over_time.csv \
   tests/fixtures/representation_usage_over_time.csv
```

### Step 5 — Run the test suite

```
python -m pytest tests/test_predictive_problem_table.py::test_table3_golden_fixture \
                 tests/test_la_review_figure_data.py::test_table2_golden_fixture \
                 tests/test_la_review_figure_data.py::test_figure2_golden_csv -v
```

All three snapshot tests must pass before committing.

### Step 6 — Commit with a traceable message

```
git add tests/fixtures/
git commit -m "chore(fixtures): refresh golden snapshots — taxonomy v1.x, <reason>"
```

The commit message must reference:
- The taxonomy version stamp (e.g., `v1.1`)
- The reason for the refresh (e.g., `added cv_design dimension`, `re-pull 2026-06`)

---

## Notebook smoke tests (d-013: run separately, not chained)

The five LA-review notebooks must each be smoke-tested with **separate** `nbconvert`
calls, not chained with `&&`:

```
jupyter nbconvert --to notebook --execute notebooks/la_review/00_environment_check.ipynb
jupyter nbconvert --to notebook --execute notebooks/la_review/01_data_audit.ipynb
jupyter nbconvert --to notebook --execute notebooks/la_review/02_task_tables_and_table3.ipynb
jupyter nbconvert --to notebook --execute notebooks/la_review/03_figures.ipynb
jupyter nbconvert --to notebook --execute notebooks/la_review/04_story_and_caption_check.ipynb
```

Check each notebook for zero cell errors before proceeding to the next.  Chaining
with `&&` is prohibited (d-013) because a failure in one notebook would silently skip
the others.

---

## Taxonomy version stamp contract (d-013)

The `manual_overrides.yaml` file must carry a `taxonomy_version_stamp` header field
that matches the `version` field in `learning_analytics_taxonomy.yaml`.  Example:

```yaml
# manual_overrides.yaml
taxonomy_version_stamp: "1.1"
overrides:
  - contribution_id: c-001
    target_construct: dropout_or_withdrawal
    rationale: "Paper predicts course dropout despite 'grade' in title"
```

A mismatch between the stamp and the YAML version is caught by the audit gate
(`run_audit_gate()`) and blocks manuscript export.
