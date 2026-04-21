"""Tests for ExtractionTemplate.validate_extraction_row()."""
import pytest
from notion_zotero.schemas.templates.generic import TEMPLATES, prediction_modeling


def test_valid_row_no_errors():
    row = {"Metric": "AUC", "Value": "0.91"}
    errors = prediction_modeling.validate_extraction_row(row)
    assert errors == []


def test_missing_required_column_returns_error():
    errors = prediction_modeling.validate_extraction_row({})
    assert len(errors) >= 2
    assert any("Metric" in e for e in errors)
    assert any("Value" in e for e in errors)


def test_partial_missing_returns_one_error():
    row = {"Metric": "F1"}  # Value missing
    errors = prediction_modeling.validate_extraction_row(row)
    assert len(errors) == 1
    assert "Value" in errors[0]


def test_alias_satisfies_required_column():
    # "score" is an alias for "Metric"
    row = {"score": "F1", "value": "0.85"}
    errors = prediction_modeling.validate_extraction_row(row)
    assert errors == []


def test_all_templates_have_validate_method():
    for tid, template in TEMPLATES.items():
        assert hasattr(template, "validate_extraction_row"), (
            f"Template {tid!r} missing validate_extraction_row()"
        )
        result = template.validate_extraction_row({})
        assert isinstance(result, list), (
            f"Template {tid!r} validate_extraction_row() must return a list"
        )


def test_templates_with_required_columns_detect_missing():
    for tid, template in TEMPLATES.items():
        required_cols = [c for c in template.expected_columns if c.required]
        if not required_cols:
            continue
        errors = template.validate_extraction_row({})
        assert errors, (
            f"Template {tid!r} has required columns but validate_extraction_row({{}}) "
            f"returned no errors"
        )
