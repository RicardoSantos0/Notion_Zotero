"""notion_schemas.py — minimal schema builders for Notion pages/databases.

These helpers build small dictionary shapes used when creating or updating pages
in tests or during local migrations.
"""

from __future__ import annotations

from typing import Any


def build_title_prop(text: str) -> dict[str, Any]:
    return {"type": "title", "title": [{"type": "text", "text": {"content": text}, "plain_text": text}]}


def build_rich_text(text: str) -> dict[str, Any]:
    return {"type": "rich_text", "rich_text": [{"type": "text", "text": {"content": text}, "plain_text": text}]}
"""Notion database schema builders used by setup and publishing flows."""

from typing import Any


def build_paper_properties() -> dict[str, Any]:
    """Return the Paper database v3 property schema.

    Preserves all v1 field types exactly:
    - Section read fields as checkboxes (Abstract ✓, Methods ✓, …)
    - Type, Article Type, Keywords, Work Nature, Learner Representation as multi_select
    - Year as number
    - Status / Reading Progress as native Notion status
    - New Zotero fields: DOI, Zotero Key, Abstract Text, URL, Reading Notes
    """
    return {
        "Title": {"title": {}},
        "Author": {"rich_text": {}},
        "Year": {"number": {"format": "number"}},
        "Journal": {"rich_text": {}},
        "DOI": {"rich_text": {}},
        "Zotero Key": {"rich_text": {}},
        "Abstract Text": {"rich_text": {}},
        "URL": {"url": {}},
        "Reading Notes": {"rich_text": {}},
        "Status": {"status": {}},
        "Reading Progress": {"status": {}},
        "Type": {"multi_select": {}},
        "Article Type": {"multi_select": {}},
        "Keywords": {"multi_select": {}},
        "Work Nature": {"multi_select": {}},
        "Learner Representation": {"multi_select": {}},
        "Learner Population": {"select": {}},
        "Deployed/Deployable": {"select": {}},
        "Course-Agnostic Approach": {"checkbox": {}},
        "Platform": {"rich_text": {}},
        "Search Strategy": {"rich_text": {}},
        "Date of Retrieval": {"date": {}},
        "Completed": {"date": {}},
        "Motive For Exclusion": {"rich_text": {}},
        "Abstract ✓": {"checkbox": {}},
        "Introduction ✓": {"checkbox": {}},
        "Methods ✓": {"checkbox": {}},
        "Results ✓": {"checkbox": {}},
        "Discussion ✓": {"checkbox": {}},
        "Conclusion ✓": {"checkbox": {}},
        "Related Work ✓": {"checkbox": {}},
        "Limitations ✓": {"checkbox": {}},
        "AI Summary": {"rich_text": {}},
    }


def build_paper_summaries_properties_v3(paper_platform_ds_id: str) -> dict[str, Any]:
    """Return the Paper Summaries v3 property schema.

    Flat schema covering all task types (PRED/DESC/KT/REC).
    Source Row tracks ordering when a paper has multiple rows for the same task.
    Theoretical Model fixes the typo from v2.
    """
    return {
        "Summary Row ID": {"title": {}},
        "Paper": {
            "relation": {
                "data_source_id": paper_platform_ds_id,
                "single_property": {},
            }
        },
        "Task Type": {
            "select": {
                "options": [
                    {"name": "PRED", "color": "blue"},
                    {"name": "DESC", "color": "green"},
                    {"name": "KT", "color": "yellow"},
                    {"name": "REC", "color": "purple"},
                ]
            }
        },
        "Source Row": {"number": {"format": "number"}},
        "Author": {"rich_text": {}},
        "Paper Name": {"rich_text": {}},
        "Context": {"rich_text": {}},
        "Teaching Method": {"rich_text": {}},
        "Students": {"rich_text": {}},
        "Courses": {"rich_text": {}},
        "Data sources": {"rich_text": {}},
        "Preprocessing Details": {"rich_text": {}},
        "Features": {"rich_text": {}},
        "Models": {"rich_text": {}},
        "Performance Metric: Best Model": {"rich_text": {}},
        "Comments": {"rich_text": {}},
        "Limitations": {"rich_text": {}},
        # PRED / KT
        "Student Performance Definition": {"rich_text": {}},
        "Target": {"rich_text": {}},
        "Assessment Strategy": {"rich_text": {}},
        "Moment of Prediction": {"rich_text": {}},
        # KT only
        "Flaw of Previous Models": {"rich_text": {}},
        "Novelty of Model": {"rich_text": {}},
        # DESC only
        "Theoretical Grounding": {"rich_text": {}},
        "Groups Created": {"rich_text": {}},
        "Cluster Description": {"rich_text": {}},
        "Implications": {"rich_text": {}},
        # REC only
        "Recommender System Type": {"rich_text": {}},
        "Target of Recommendation": {"rich_text": {}},
        "Initialization Method": {"rich_text": {}},
        "Updates to Recommendations": {"rich_text": {}},
        "Recommendation types": {"rich_text": {}},
        "Evaluation": {"rich_text": {}},
        # Metadata
        "Theoretical Model": {"rich_text": {}},
        "Last Modified": {"date": {}},
        "Revision Notes": {"rich_text": {}},
    }


def build_paper_summaries_properties(paper_platform_ds_id: str) -> dict[str, Any]:
    """Alias for build_paper_summaries_properties_v3 — kept for backward compatibility."""
    return build_paper_summaries_properties_v3(paper_platform_ds_id)
