"""Tests for the refactored analysis layer.

Covers:
- core/text_utils.py        (no pandas required)
- analysis/summarizer.py    (no pandas required for build_summary_tables)
- analysis/cleaner.py       (pandas required; skipped when not installed)
- analysis/__init__.py      (run_analysis, export_database_snapshot)
- analysis/original_db_summary.py  (backwards compat)
"""
from __future__ import annotations

import json
import pytest

# ---------------------------------------------------------------------------
# pandas availability guard
# ---------------------------------------------------------------------------

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

requires_pandas = pytest.mark.skipif(not HAS_PANDAS, reason="pandas not installed")


# ---------------------------------------------------------------------------
# core/text_utils.py
# ---------------------------------------------------------------------------

class TestCleanWhitespace:
    def test_collapses_multiple_spaces(self):
        from notion_zotero.core.text_utils import clean_whitespace
        assert clean_whitespace("hello   world") == "hello world"

    def test_normalises_crlf(self):
        from notion_zotero.core.text_utils import clean_whitespace
        assert "\r" not in clean_whitespace("a\r\nb")

    def test_trims_pipe_spacing(self):
        from notion_zotero.core.text_utils import clean_whitespace
        assert clean_whitespace("a  |  b") == "a | b"

    def test_trims_semicolon_spacing(self):
        from notion_zotero.core.text_utils import clean_whitespace
        assert clean_whitespace("a  ;  b") == "a; b"

    def test_strips_leading_trailing(self):
        from notion_zotero.core.text_utils import clean_whitespace
        assert clean_whitespace("  hello  ") == "hello"

    def test_empty_string(self):
        from notion_zotero.core.text_utils import clean_whitespace
        assert clean_whitespace("") == ""


class TestApplyRegexFixes:
    def test_applies_single_fix(self):
        from notion_zotero.core.text_utils import apply_regex_fixes
        result = apply_regex_fixes("Fiiltering data", {r"\bFiiltering\b": "Filtering"})
        assert result == "Filtering data"

    def test_case_insensitive(self):
        from notion_zotero.core.text_utils import apply_regex_fixes
        result = apply_regex_fixes("FIILTERING", {r"\bFiiltering\b": "Filtering"})
        assert result == "Filtering"

    def test_multiple_fixes(self):
        from notion_zotero.core.text_utils import apply_regex_fixes
        result = apply_regex_fixes("Fiiltering Exerrcise", {
            r"\bFiiltering\b": "Filtering",
            r"\bExerrcise\b": "Exercise",
        })
        assert result == "Filtering Exercise"

    def test_empty_fixes_noop(self):
        from notion_zotero.core.text_utils import apply_regex_fixes
        assert apply_regex_fixes("hello", {}) == "hello"


class TestNormalizeCell:
    def test_non_string_passthrough(self):
        from notion_zotero.core.text_utils import normalize_cell
        assert normalize_cell(42) == 42
        assert normalize_cell(None) is None
        assert normalize_cell([1, 2]) == [1, 2]

    def test_whitespace_cleaned(self):
        from notion_zotero.core.text_utils import normalize_cell
        assert normalize_cell("  hello   world  ") == "hello world"

    def test_fixes_applied(self):
        from notion_zotero.core.text_utils import normalize_cell
        result = normalize_cell("Fiiltering", fixes={r"\bFiiltering\b": "Filtering"})
        assert result == "Filtering"

    def test_value_map_lookup(self):
        from notion_zotero.core.text_utils import normalize_cell
        result = normalize_cell("n/a", value_map={"n/a": "Not Applicable"})
        assert result == "Not Applicable"

    def test_value_map_case_insensitive_key(self):
        from notion_zotero.core.text_utils import normalize_cell
        result = normalize_cell("N/A", value_map={"n/a": "Not Applicable"})
        assert result == "Not Applicable"

    def test_no_maps_returns_cleaned(self):
        from notion_zotero.core.text_utils import normalize_cell
        assert normalize_cell("  hello  ") == "hello"


class TestNormalizeSearchString:
    def test_non_string_passthrough(self):
        from notion_zotero.core.text_utils import normalize_search_string
        assert normalize_search_string(None) is None

    def test_and_terms_quoted_and_joined(self):
        from notion_zotero.core.text_utils import normalize_search_string
        result = normalize_search_string("machine learning AND deep learning")
        assert '"machine learning" AND "deep learning"' == result

    def test_and_terms_deduplicated(self):
        from notion_zotero.core.text_utils import normalize_search_string
        result = normalize_search_string("foo AND foo AND bar")
        assert result.count('"foo"') == 1

    def test_typographic_quotes_replaced(self):
        from notion_zotero.core.text_utils import normalize_search_string
        result = normalize_search_string("“hello”")
        assert "“" not in result
        assert "”" not in result

    def test_single_term_no_and(self):
        from notion_zotero.core.text_utils import normalize_search_string
        result = normalize_search_string("machine learning")
        assert result == "machine learning"


# ---------------------------------------------------------------------------
# analysis/summarizer.py
# ---------------------------------------------------------------------------

def _make_bundle(ref_id="ref-1", task_name="prediction", rows=None):
    return {
        "references": [{"id": ref_id, "title": "Test Paper", "provenance": {"source_id": ref_id}}],
        "tasks": [{"id": "task-1", "name": task_name}],
        "reference_tasks": [{"id": "rt-1", "task_id": "task-1"}],
        "task_extractions": [
            {
                "id": "ex-1",
                "reference_task_id": "rt-1",
                "schema_name": task_name,
                "extracted": rows or [{"col_a": "val_a", "col_b": "val_b"}],
            }
        ],
        "provenance": {"source_id": ref_id},
    }


class TestBuildSummaryTables:
    def test_reading_list_present(self):
        from notion_zotero.analysis.summarizer import build_summary_tables
        tables = build_summary_tables([_make_bundle()])
        assert "Reading List" in tables

    def test_reading_list_has_one_row_per_bundle(self):
        from notion_zotero.analysis.summarizer import build_summary_tables
        tables = build_summary_tables([_make_bundle("r1"), _make_bundle("r2")])
        assert len(tables["Reading List"]) == 2

    def test_task_label_discovered_from_data(self):
        from notion_zotero.analysis.summarizer import build_summary_tables
        tables = build_summary_tables([_make_bundle(task_name="my_custom_task")])
        assert "my_custom_task" in tables

    def test_task_label_fn_applied(self):
        from notion_zotero.analysis.summarizer import build_summary_tables
        tables = build_summary_tables(
            [_make_bundle(task_name="prediction")],
            task_label_fn=lambda n: "PRED" if "pred" in n.lower() else n,
        )
        assert "PRED" in tables

    def test_empty_bundles_returns_empty_reading_list(self):
        from notion_zotero.analysis.summarizer import build_summary_tables
        tables = build_summary_tables([])
        assert tables["Reading List"] == []

    def test_extraction_rows_include_source_fields(self):
        from notion_zotero.analysis.summarizer import build_summary_tables
        tables = build_summary_tables([_make_bundle(ref_id="r1", task_name="desc")])
        row = tables["desc"][0]
        assert row["source_page_id"] == "r1"
        assert row["col_a"] == "val_a"

    def test_load_canonical_records_empty_dir(self, tmp_path):
        from notion_zotero.analysis.summarizer import load_canonical_records
        assert load_canonical_records(tmp_path) == []

    def test_load_canonical_records_loads_json(self, tmp_path):
        from notion_zotero.analysis.summarizer import load_canonical_records
        bundle = _make_bundle()
        (tmp_path / "r1.canonical.json").write_text(
            json.dumps(bundle), encoding="utf-8"
        )
        records = load_canonical_records(tmp_path)
        assert len(records) == 1

    def test_load_canonical_records_skips_bad_json(self, tmp_path):
        from notion_zotero.analysis.summarizer import load_canonical_records
        (tmp_path / "bad.canonical.json").write_text("NOT JSON", encoding="utf-8")
        assert load_canonical_records(tmp_path) == []


@requires_pandas
class TestBuildSummaryDataframes:
    def test_returns_dataframes(self):
        from notion_zotero.analysis.summarizer import build_summary_dataframes
        dfs = build_summary_dataframes([_make_bundle()])
        for df in dfs.values():
            assert hasattr(df, "columns")

    def test_reading_list_df_not_empty(self):
        from notion_zotero.analysis.summarizer import build_summary_dataframes
        dfs = build_summary_dataframes([_make_bundle()])
        assert len(dfs["Reading List"]) == 1


# ---------------------------------------------------------------------------
# analysis/cleaner.py
# ---------------------------------------------------------------------------

@requires_pandas
class TestCleanTable:
    def _df(self, data):
        return pd.DataFrame(data)

    def test_returns_df_and_log(self):
        from notion_zotero.analysis.cleaner import clean_table
        df = self._df({"col": ["hello  world"]})
        cleaned, log = clean_table(df)
        assert "rows_before" in log
        assert "rows_after" in log

    def test_whitespace_normalised(self):
        from notion_zotero.analysis.cleaner import clean_table
        df = self._df({"col": ["  hello   world  "]})
        cleaned, _ = clean_table(df)
        assert cleaned["col"].iloc[0] == "hello world"

    def test_typo_fixes_applied(self):
        from notion_zotero.analysis.cleaner import clean_table
        df = self._df({"col": ["Fiiltering"]})
        cleaned, log = clean_table(df, typo_fixes={r"\bFiiltering\b": "Filtering"})
        assert cleaned["col"].iloc[0] == "Filtering"
        assert log["text_updates"] >= 1

    def test_value_map_applied(self):
        from notion_zotero.analysis.cleaner import clean_table
        df = self._df({"col": ["n/a"]})
        cleaned, _ = clean_table(df, value_map={"n/a": "Not Applicable"})
        assert cleaned["col"].iloc[0] == "Not Applicable"

    def test_no_fixes_noop_on_clean_text(self):
        from notion_zotero.analysis.cleaner import clean_table
        df = self._df({"col": ["clean text"]})
        cleaned, log = clean_table(df)
        assert cleaned["col"].iloc[0] == "clean text"
        assert log["text_updates"] == 0

    def test_search_strategy_column_normalised(self):
        from notion_zotero.analysis.cleaner import clean_table
        df = self._df({"Search Strategy": ["machine learning AND deep learning"]})
        cleaned, log = clean_table(df, search_strategy_columns=["Search Strategy"])
        assert "AND" in cleaned["Search Strategy"].iloc[0]
        assert log["search_strategy_updates"] >= 1

    def test_numeric_column_unchanged(self):
        from notion_zotero.analysis.cleaner import clean_table
        df = self._df({"year": [2023, 2024]})
        cleaned, _ = clean_table(df)
        assert list(cleaned["year"]) == [2023, 2024]


# ---------------------------------------------------------------------------
# analysis/__init__.py — run_analysis and export_database_snapshot
# ---------------------------------------------------------------------------

@requires_pandas
class TestAnalysisInit:
    def test_run_analysis_returns_three_values(self, tmp_path):
        from notion_zotero.analysis import run_analysis
        bundle = _make_bundle()
        (tmp_path / "r1.canonical.json").write_text(json.dumps(bundle), encoding="utf-8")
        raw, clean, norm_log = run_analysis(tmp_path)
        assert "Reading List" in raw
        assert "Reading List" in clean
        assert isinstance(norm_log, dict)

    def test_export_database_snapshot_writes_file(self, tmp_path, monkeypatch):
        from notion_zotero.analysis import export_database_snapshot
        monkeypatch.chdir(tmp_path)
        (tmp_path / "fixtures" / "reading_list").mkdir(parents=True)
        out = tmp_path / "out.json"
        export_database_snapshot(str(out))
        assert out.exists()


# ---------------------------------------------------------------------------
# analysis/original_db_summary.py — backwards compatibility
# ---------------------------------------------------------------------------

@requires_pandas
class TestOriginalDbSummaryCompat:
    def test_task_order_importable(self):
        from notion_zotero.analysis.original_db_summary import TASK_ORDER
        assert "PRED" in TASK_ORDER

    def test_task_label_from_name_pred(self):
        from notion_zotero.analysis.original_db_summary import _task_label_from_name
        assert _task_label_from_name("prediction") == "PRED"

    def test_task_label_from_name_kt(self):
        from notion_zotero.analysis.original_db_summary import _task_label_from_name
        assert _task_label_from_name("knowledge tracing") == "KT"

    def test_task_label_unknown(self):
        from notion_zotero.analysis.original_db_summary import _task_label_from_name
        result = _task_label_from_name("something_else")
        assert isinstance(result, str)

    def test_concatenate_summary_tables_returns_tuple(self):
        from notion_zotero.analysis.original_db_summary import concatenate_summary_tables
        dfs, errors = concatenate_summary_tables([_make_bundle(task_name="prediction")])
        assert "Reading List + Page Fields" in dfs
        assert isinstance(errors, list)

    def test_standard_clean_table_returns_tuple(self):
        from notion_zotero.analysis.original_db_summary import standard_clean_table
        df = pd.DataFrame({"col": ["n/a", "  hello  "]})
        cleaned, log = standard_clean_table(df, "test_table")
        assert "rows_before" in log
        assert log["table"] == "test_table"

    def test_normalize_text_cell_compat(self):
        from notion_zotero.analysis.original_db_summary import _normalize_text_cell
        result = _normalize_text_cell("n/a")
        assert result == "Not Applicable"

    def test_clean_whitespace_compat(self):
        from notion_zotero.analysis.original_db_summary import _clean_whitespace
        assert _clean_whitespace("  hello  ") == "hello"

    def test_load_credentials_missing(self, monkeypatch):
        from notion_zotero.analysis.original_db_summary import load_credentials
        monkeypatch.delenv("NOTION_API_KEY", raising=False)
        monkeypatch.delenv("NOTION_DATABASE_ID", raising=False)
        with pytest.raises(ValueError, match="Missing env vars"):
            load_credentials()
