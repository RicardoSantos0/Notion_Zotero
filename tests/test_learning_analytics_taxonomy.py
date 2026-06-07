"""Test stubs for the Learning Analytics taxonomy YAML and domain pack.

Test-first milestone M1 / task T1.2.
All tests xfail (strict=False) until implementation tasks T2.2 complete.

Spec IDs covered:
  - test-R-002-001  (education_learning_analytics.py loads from YAML, version >=1.1)
  - test-R-013-001  (fairness_addressed and ethics_discussion fields present)

Golden-fixture refresh procedure (d-013)
----------------------------------------
When the taxonomy YAML or classifier output is intentionally changed:
  1. Run the full classifier pipeline against the canonical dataset:
         python -m notion_zotero.analysis.pred_horizon_summary --refresh-fixtures
     or the equivalent notebook cell in 01_data_audit.ipynb.
  2. Verify the diff in tests/fixtures/ is intentional (git diff tests/fixtures/).
  3. Copy the new CSV outputs into tests/fixtures/ with a commit message
     referencing the taxonomy_version_stamp from manual_overrides.yaml.
  4. Update CHANGELOG.md with the new version entry.
  5. Re-run the test suite to confirm golden tests pass with the new snapshots.

Taxonomy version stamp:  The taxonomy YAML must include a `version` field (>=1.1)
and the manual_overrides.yaml must carry a `taxonomy_version_stamp` header
matching the YAML version (d-013 constraint).
"""
from __future__ import annotations

import pytest

# ---------------------------------------------------------------------------
# test-R-002-001
# ---------------------------------------------------------------------------


def test_taxonomy_loaded_from_yaml():
    """education_learning_analytics.py must load its vocabulary from
    learning_analytics_taxonomy.yaml (not hardcoded Python dicts).

    Spec: test-R-002-001
    Requirement: R-002
    Evidence command: pytest tests/test_learning_analytics_taxonomy.py::test_taxonomy_loaded_from_yaml
    """
    from notion_zotero.schemas.domain_packs.education_learning_analytics import (
        DOMAIN_PACK_VERSION,
        TAXONOMY_SOURCE,  # expected new constant pointing at the YAML path
    )
    from packaging.version import Version  # type: ignore[import]

    # The domain pack version must be >= 1.1
    assert Version(DOMAIN_PACK_VERSION) >= Version("1.1"), (
        f"DOMAIN_PACK_VERSION is {DOMAIN_PACK_VERSION!r}; expected >= '1.1' "
        "(WP1 T2.2 updates the pack version)"
    )

    # The taxonomy must have been loaded from a YAML file, not hardcoded dicts
    assert TAXONOMY_SOURCE is not None, "TAXONOMY_SOURCE constant not set — YAML not loaded"
    assert str(TAXONOMY_SOURCE).endswith(".yaml"), (
        f"TAXONOMY_SOURCE {TAXONOMY_SOURCE!r} does not point at a .yaml file"
    )

    # The YAML file must exist on disk
    import pathlib
    yaml_path = pathlib.Path(TAXONOMY_SOURCE)
    assert yaml_path.exists(), f"Taxonomy YAML not found at {yaml_path}"


def test_taxonomy_has_required_10_dimensions():
    """The taxonomy YAML must define all 10 dimensions from the NLP specialist spec.

    Spec: test-R-002-001 (extension — covers d-011 additions)
    Requirement: R-002, R-004
    """
    from notion_zotero.schemas.domain_packs.education_learning_analytics import (
        get_taxonomy,  # expected new function loading from YAML
    )

    taxonomy = get_taxonomy()
    assert isinstance(taxonomy, dict), "get_taxonomy() must return a dict"

    required_dimensions = [
        "supervised_ml_task",
        "outcome_scope",
        "unit_of_analysis",
        "target_construct",
        "prediction_timing",
        "actionability_status",
        "risk_framing",
        "evidence_quality",
        "cv_design",      # d-011 addition
        "context_type",   # d-011 addition (HEI/MOOC/ITS)
    ]
    for dim in required_dimensions:
        assert dim in taxonomy, (
            f"Dimension {dim!r} missing from taxonomy — check learning_analytics_taxonomy.yaml"
        )

    # Each dimension must have a non-empty vocabulary list
    for dim in required_dimensions:
        vocab = taxonomy[dim].get("vocabulary", [])
        assert len(vocab) > 0, f"Dimension {dim!r} has an empty vocabulary"


def test_taxonomy_d011_additions_present():
    """d-011 additions must appear in the taxonomy: cv_design in evidence_quality;
    context_type (HEI/MOOC/ITS) in unit_of_analysis.

    Spec: test-R-002-001 (d-011 constraint)
    Requirement: R-002
    """
    from notion_zotero.schemas.domain_packs.education_learning_analytics import (
        get_taxonomy,
    )

    taxonomy = get_taxonomy()

    # cv_design must be present as a top-level dimension or nested under evidence_quality
    assert "cv_design" in taxonomy, (
        "cv_design dimension missing — required by d-011"
    )
    cv_vocab = taxonomy["cv_design"].get("vocabulary", [])
    assert "temporal_or_prospective" in cv_vocab, (
        "cv_design vocabulary must include 'temporal_or_prospective' (d-011)"
    )

    # context_type must be present with HEI/MOOC/ITS
    assert "context_type" in taxonomy, (
        "context_type dimension missing — required by d-011"
    )
    ctx_vocab = taxonomy["context_type"].get("vocabulary", [])
    for required_ctx in ("HEI", "MOOC", "ITS"):
        assert required_ctx in ctx_vocab, (
            f"context_type vocabulary missing {required_ctx!r} — required by d-011"
        )


def test_changelog_exists_with_v11_migration_note():
    """A CHANGELOG.md must exist at the package root with a v1.0->v1.1 migration note.

    Spec: test-R-002-001
    Requirement: R-002
    """
    import pathlib

    repo_root = pathlib.Path(__file__).resolve().parents[1]
    changelog = repo_root / "CHANGELOG.md"
    assert changelog.exists(), f"CHANGELOG.md not found at {changelog}"

    text = changelog.read_text(encoding="utf-8")
    assert "1.1" in text, (
        "CHANGELOG.md must include a v1.1 entry documenting the YAML migration"
    )


# ---------------------------------------------------------------------------
# test-R-013-001
# ---------------------------------------------------------------------------


def test_fairness_fields_present():
    """Classifier output must include fairness_addressed and ethics_discussion fields.

    Spec: test-R-013-001
    Requirement: R-013
    Evidence command: pytest tests/test_learning_analytics_taxonomy.py::test_fairness_fields_present
    """
    from notion_zotero.schemas.domain_packs.education_learning_analytics import (
        get_taxonomy,
    )

    taxonomy = get_taxonomy()

    # fairness_addressed must be present with allowed label set
    assert "fairness_addressed" in taxonomy, (
        "fairness_addressed dimension missing from taxonomy (R-013 / T6.2)"
    )
    fairness_vocab = set(taxonomy["fairness_addressed"].get("vocabulary", []))
    expected = {"yes", "no", "unclear"}
    assert expected.issubset(fairness_vocab), (
        f"fairness_addressed vocabulary {fairness_vocab} missing required labels {expected - fairness_vocab}"
    )

    # ethics_discussion must be present with allowed label set
    assert "ethics_discussion" in taxonomy, (
        "ethics_discussion dimension missing from taxonomy (R-013 / T6.2)"
    )
    ethics_vocab = set(taxonomy["ethics_discussion"].get("vocabulary", []))
    assert expected.issubset(ethics_vocab), (
        f"ethics_discussion vocabulary {ethics_vocab} missing required labels {expected - ethics_vocab}"
    )
