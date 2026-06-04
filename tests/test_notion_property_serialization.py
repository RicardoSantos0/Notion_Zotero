from __future__ import annotations


def test_serialize_notion_property_infers_canonical_types():
    from notion_zotero.writers.notion_properties import serialize_notion_properties

    payload = serialize_notion_properties(
        {
            "title": "A paper",
            "authors": ["Alice", "Bob"],
            "year": 2024,
            "doi": "10.1000/example",
            "tags": ["LA", "KT"],
        }
    )

    assert payload["title"] == {"title": [{"text": {"content": "A paper"}}]}
    assert payload["authors"] == {"multi_select": [{"name": "Alice"}, {"name": "Bob"}]}
    assert payload["year"] == {"number": 2024}
    assert payload["doi"] == {"rich_text": [{"text": {"content": "10.1000/example"}}]}
    assert payload["tags"] == {"multi_select": [{"name": "LA"}, {"name": "KT"}]}


def test_serialize_notion_property_uses_schema_property_name_and_type():
    from notion_zotero.writers.notion_properties import serialize_notion_properties

    payload = serialize_notion_properties(
        {"doi": "10.1000/example"},
        {"doi": {"name": "DOI", "type": "url"}},
    )

    assert payload == {"DOI": {"url": "10.1000/example"}}


def test_build_property_schema_from_notion_schema_maps_canonical_aliases():
    from notion_zotero.writers.notion_properties import (
        build_property_schema_from_notion_schema,
        serialize_notion_properties,
    )

    schema = build_property_schema_from_notion_schema(
        {
            "Paper Title": {"type": "title"},
            "Publication Year": {"type": "number"},
            "DOI": "rich_text",
            "Workflow Status": {"type": "status"},
        }
    )

    assert schema == {
        "title": {"name": "Paper Title", "type": "title"},
        "doi": {"name": "DOI", "type": "rich_text"},
        "year": {"name": "Publication Year", "type": "number"},
    }
    assert serialize_notion_properties({"doi": "10.1000/example"}, schema) == {
        "DOI": {"rich_text": [{"text": {"content": "10.1000/example"}}]}
    }
