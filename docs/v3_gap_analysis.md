# V3 Gap Analysis

Comparison of legacy Notion Reading List schema (pre-migration) against the current canonical model.

## Field Coverage

| Legacy Property | Canonical Field | Status | Notes |
|----------------|----------------|--------|-------|
| `Title` / `Name` | `Reference.title` | ✅ Mapped | Both aliases handled |
| `Author` / `Authors` | `Reference.authors` | ✅ Mapped | Importer splits on `;` or `,` |
| `Year` | `Reference.year` | ✅ Mapped | Stored as integer |
| `Journal` | `Reference.journal` | ✅ Mapped | |
| `DOI` | `Reference.doi` | ✅ Mapped | Normalised on import |
| `URL` | `Reference.url` | ✅ Mapped | |
| `Zotero Key` | `Reference.zotero_key` | ✅ Mapped | |
| `Abstract Text` | `Reference.abstract` | ✅ Mapped | |
| `Article Type` | `Reference.item_type` | ✅ Mapped | |
| `Keywords` / `Tags` | `Reference.tags` | ✅ Mapped | |
| `Status` | `WorkflowState.state` + `ReferenceTask` | ✅ Mapped | Via `status_mapping.py` rules |
| `Status_1` | `WorkflowState` / `ReferenceTask` | ✅ Mapped | Secondary status decoded separately |

## Structural Differences

| Aspect | Legacy | Current | Impact |
|--------|--------|---------|--------|
| **IDs** | Random UUID fragments | Deterministic (page_id + task + index) | Re-running produces stable output |
| **Provenance** | None | Mandatory `provenance` dict on every object | New objects carry full origin trace |
| **Task creation** | Any heading → task (ad hoc) | Only domain-pack-declared tasks | Fewer spurious tasks; no fake `Summary`, `Dataset` tasks |
| **Template matching** | None | Heading → task → template via domain pack | Structured validation of extracted tables |
| **Status decoding** | Hard-coded strings | `status_mapping.py` rules | Centrally auditable; extensible |
| **Workflow vs assignment** | Mixed in `Status` | Separate `WorkflowState` and `ReferenceTask` | Clearer semantics |

## Missing in Legacy (Not Covered)

| Canonical Field | Availability in Legacy | Action Required |
|----------------|----------------------|-----------------|
| `Reference.provenance` | Not present | Auto-populated by new importer from page metadata |
| `Task.template_id` | Not present | Derived from domain pack |
| `ReferenceTask.assignment_source` | Not tracked | New importer records which field drove the assignment |
| `TaskExtraction.raw_headers` | Not stored | New importer captures table headers before normalisation |
| `TaskExtraction.validation` | Not present | Template validation runs automatically |

## Legacy Properties With No Direct Canonical Mapping

| Legacy Property | Recommendation |
|----------------|---------------|
| `Summary Table` (heading) | Dropped — not a domain-pack-declared task unless pack defines it |
| `Methods` (heading) | Use `methods_table` template; add to domain pack if needed |
| `Dataset` (heading) | Use `dataset_table` template; add to domain pack if needed |
| Inline note paragraphs | Captured as `Annotation` objects (kind=`note`) |

## Recommendation

Run `legacy/migration_audit.py --legacy fixtures/reading_list --report docs/v3_gap_analysis_auto.md` on your fixture directory to generate a per-page gap report from your actual data.
