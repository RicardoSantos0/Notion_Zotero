from notion_zotero.schemas import templates
from notion_zotero.schemas import task_registry
from notion_zotero.schemas.domain_packs import education_learning_analytics as ela


def test_templates_exported():
    assert isinstance(templates.TEMPLATES, dict)
    # core seeds
    assert "prediction_modeling" in templates.TEMPLATES
    assert "descriptive_analysis" in templates.TEMPLATES


def test_domain_pack_heading_mapping_and_template_exists():
    heading = "Prediction results"
    tid = task_registry.match_heading_to_task(heading)
    assert tid == "performance_prediction"
    meta = ela.domain_pack["tasks"][tid]
    template_id = meta.get("template_id")
    assert template_id in templates.TEMPLATES


def test_generic_templates_have_expected_columns():
    t = templates.TEMPLATES.get("metrics_table")
    assert t is not None
    names = [c.name.lower() for c in t.expected_columns]
    assert any("metric" in n for n in names)
