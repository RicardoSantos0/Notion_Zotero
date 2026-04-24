"""Integration tests for the reading list importer."""
from __future__ import annotations

import json
from pathlib import Path

GOLDEN = Path(__file__).parent / "fixtures" / "golden"
SAMPLE = Path(__file__).parent / "fixtures" / "sample_page.json"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_golden_ela_page_has_required_fields():
    data = _load_json(GOLDEN / "education_learning_analytics_page.json")
    props = data.get("properties", {})
    assert "Title" in props or "Name" in props, "Page must have a Title or Name property"
    assert "Status" in props, "ELA fixture must have a Status property"


def test_golden_generic_page_has_children():
    data = _load_json(GOLDEN / "generic_template_page.json")
    assert isinstance(data.get("children"), list)
    assert len(data["children"]) > 0


def test_task_registry_resolves_ela_heading():
    from notion_zotero.schemas.task_registry import match_heading_to_task
    tid = match_heading_to_task("Knowledge Tracing Results")
    assert tid == "knowledge_tracing", f"Expected knowledge_tracing, got {tid}"


def test_task_registry_resolves_prediction_heading():
    from notion_zotero.schemas.task_registry import match_heading_to_task
    tid = match_heading_to_task("Prediction Results")
    assert tid == "performance_prediction", f"Expected performance_prediction, got {tid}"


def test_domain_pack_task_has_template():
    from notion_zotero.schemas.task_registry import load_domain_pack
    from notion_zotero.schemas.templates.generic import TEMPLATES
    pack = load_domain_pack("education_learning_analytics")
    assert pack is not None, "education_learning_analytics pack must be registered"
    for tid, meta in pack["tasks"].items():
        tmpl_id = meta.get("template_id")
        assert tmpl_id in TEMPLATES, f"Task {tid} maps to missing template {tmpl_id}"


def test_list_domain_packs_returns_nonempty():
    from notion_zotero.schemas.task_registry import list_domain_packs
    packs = list_domain_packs()
    assert len(packs) > 0, "At least one domain pack must be registered"
    assert "education_learning_analytics" in packs


def test_templates_dict_is_nonempty():
    from notion_zotero.schemas.templates.generic import TEMPLATES
    assert len(TEMPLATES) >= 6, f"Expected at least 6 templates, got {len(TEMPLATES)}"


def test_exceptions_hierarchy():
    from notion_zotero.core.exceptions import (
        NotionZoteroError,
        NotionImportError,
        FieldMappingError,
        DomainPackError,
    )
    assert issubclass(NotionImportError, NotionZoteroError)
    assert issubclass(FieldMappingError, NotionImportError)
    assert issubclass(DomainPackError, NotionZoteroError)
    err = FieldMappingError("doi", "reading_list")
    assert "doi" in str(err)
