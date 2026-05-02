import pytest

from notion_zotero.analysis.visualization import (
    build_multivalue_trend,
    map_value_to_group,
    parse_list_like_cell,
)


def test_parse_list_like_cell_handles_list_strings_and_delimiters():
    assert parse_list_like_cell("['A', 'B']") == ["A", "B"]
    assert parse_list_like_cell("A; B") == ["A", "B"]
    assert parse_list_like_cell(None) == []
    assert parse_list_like_cell("Not Applicable") == []


def test_map_value_to_group_uses_caller_supplied_patterns():
    patterns = {
        "G1": [r"alpha", r"first"],
        "G2": [r"beta"],
    }
    assert map_value_to_group("Accepted Alpha", patterns) == "G1"
    assert map_value_to_group("Accepted Beta", patterns, required_prefix="Accepted") == "G2"
    assert map_value_to_group("Rejected Beta", patterns, required_prefix="Accepted") is None


def test_build_multivalue_trend_without_group_when_pandas_available():
    pd = pytest.importorskip("pandas")

    data = pd.DataFrame(
        [
            {"page_id": "p1", "year": "2024", "Value": ["A"]},
            {"page_id": "p2", "year": "2024", "Value": ["B", "C"]},
            {"page_id": "p2", "year": "2024", "Value": ["B", "C"]},
        ]
    )

    trend = build_multivalue_trend(
        data,
        value_col="Value",
        selected_values=["A", "B", "C"],
    )

    counts = {
        row["value"]: row["n"]
        for row in trend.to_dict("records")
        if row["year"] == 2024
    }
    assert counts["A"] == 1
    assert counts["B"] == 1
    assert counts["C"] == 1


def test_build_multivalue_trend_with_caller_supplied_groups_when_pandas_available():
    pd = pytest.importorskip("pandas")

    data = pd.DataFrame(
        [
            {"page_id": "p1", "year": "2024", "Value": ["A"], "Status": "Accepted Alpha"},
            {"page_id": "p2", "year": "2024", "Value": ["B"], "Status": "Accepted Beta"},
        ]
    )

    trend = build_multivalue_trend(
        data,
        value_col="Value",
        selected_values=["A", "B"],
        group_source_cols=["Status"],
        group_patterns={"G1": [r"alpha"], "G2": [r"beta"]},
        group_order=["G1", "G2"],
        group_col="group",
        required_group_prefix="Accepted",
    )

    records = trend.to_dict("records")
    assert any(row["group"] == "G1" and row["value"] == "A" and row["n"] == 1 for row in records)
    assert any(row["group"] == "G2" and row["value"] == "B" and row["n"] == 1 for row in records)

