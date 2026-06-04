import pytest

pd = pytest.importorskip("pandas")

from notion_zotero.analysis.pred_horizon_summary import (
    build_pred_horizon_task_summary,
    classify_horizons,
    classify_horizons_with_source,
    classify_supervised_ml_task,
    classify_target_variable,
    classify_target_variables,
    has_implemented_intervention_or_deployment,
    is_early_actionable_prediction,
    write_pred_horizon_task_summary_workbook,
)
from notion_zotero.schemas.domain_packs.education_learning_analytics import (
    PREDICTION_HORIZON_ALIAS_PATTERNS,
)


def test_pred_horizon_classifiers_cover_core_definitions():
    short_row = {
        "Task": "Classification",
        "Student Performance Definition": "Final Grade in Course",
        "Target": "Pass vs Fail",
        "Moment of Prediction": "Week 3",
    }
    long_row = {
        "Task": "Regression",
        "Student Performance Definition": "Program dropout",
        "Target": "Dropout vs Program Completion",
        "Moment of Prediction": "End of Course",
    }
    course_dropout_row = {
        "Student Performance Definition": "Course dropout",
        "Target": "Dropout from the course",
    }
    bare_dropout_row = {
        "Student Performance Definition": "Dropout",
        "Target": "Dropout vs No Dropout",
    }

    assert classify_supervised_ml_task(short_row["Task"]) == "Classification"
    assert classify_supervised_ml_task(long_row["Task"]) == "Regression"
    assert classify_horizons(short_row) == ["Short-term"]
    assert classify_horizons(long_row) == ["Long-term"]
    assert classify_horizons(course_dropout_row) == ["Short-term"]
    assert classify_horizons(bare_dropout_row) == []
    assert classify_target_variable(short_row) == "Pass/fail"
    assert classify_target_variable(long_row) == "Dropout / retention"
    assert classify_target_variable(
        {"Student Performance Definition": "Quality of next interaction"}
    ) == "Next interaction / question outcome"
    assert classify_target_variable(
        {"Student Performance Definition": "Close to Pass Scores"}
    ) == "Grade / score / performance"
    assert classify_target_variable(
        {"Student Performance Definition": "Academic success"}
    ) == "Other / ambiguous"
    assert classify_target_variables(
        {
            "Student Performance Definition": "Final score and program dropout",
            "Target": "Final score and program dropout risk",
        }
    ) == ["Dropout / retention", "Grade / score / performance"]
    assert is_early_actionable_prediction(short_row) is True
    assert is_early_actionable_prediction(long_row) is False
    assert has_implemented_intervention_or_deployment(
        "Tested on New Students",
        "Prototype",
    ) is False
    assert has_implemented_intervention_or_deployment(
        "Tested on New Students",
        "Integrated in LMS",
    ) is True
    assert has_implemented_intervention_or_deployment(
        "Backtested with data from Previous Students",
        "Deployable",
    ) is False


def test_prediction_horizon_aliases_are_course_vs_program_level():
    short_aliases = " ".join(PREDICTION_HORIZON_ALIAS_PATTERNS["Short-term"])
    long_aliases = " ".join(PREDICTION_HORIZON_ALIAS_PATTERNS["Long-term"])

    assert "course" in short_aliases
    assert "program" in long_aliases
    assert r"dropout" not in PREDICTION_HORIZON_ALIAS_PATTERNS["Long-term"]
    assert classify_horizons(
        {
            "Student Performance Definition": "Student dropout",
            "Target": "Dropout vs No Dropout",
        }
    ) == []
    assert classify_horizons(
        {
            "Student Performance Definition": "Program dropout",
            "Target": "Dropout before degree completion",
        }
    ) == ["Long-term"]


def test_reviewed_horizon_overrides_keep_generic_dropout_out_of_aliases():
    assert classify_horizons_with_source(
        {
            "source_title": (
                "Predicting student academic performance using multi-model "
                "heterogeneous ensemble approach"
            ),
            "Student Performance Definition": "Dropout",
            "Target": "At-risk vs Not at-risk",
        }
    ) == [("Long-term", "reviewed paper-level override")]
    assert classify_horizons_with_source(
        {
            "source_title": (
                "Predicting student dropout in subscription-based online learning "
                "environments: The beneficial impact of the logit leaf model"
            ),
            "Student Performance Definition": "Cancelling Subscription Next Month",
            "Target": "Dropout vs No Dropout",
        }
    ) == [("Short-term", "reviewed paper-level override")]
    assert classify_horizons(
        {
            "Student Performance Definition": "Dropout",
            "Target": "Dropout vs No Dropout",
        }
    ) == []


def test_build_pred_horizon_task_summary_counts_unique_papers():
    dfs = {
        "Reading List": [
            {
                "page_id": "paper-1",
                "title": "Course Grade Study",
                "Work Nature": "Tested on New Students",
                "Deployed/ Deployable": "Prototype",
            },
            {
                "page_id": "paper-2",
                "title": "Dropout Study",
                "Work Nature": "Backtested with data from Previous Students",
                "Deployed/ Deployable": "Deployable",
            },
            {
                "page_id": "paper-3",
                "title": "Mixed Study",
                "Work Nature": "Backtested with data from Previous Students",
                "Deployed/ Deployable": "Integrated in LMS",
            },
        ],
        "PRED": [
            {
                "source_page_id": "paper-1",
                "source_title": "Course Grade Study",
                "Task": "Classification",
                "Student Performance Definition": "Final Grade in Course",
                "Target": "Pass vs Fail",
                "Moment of Prediction": "Week 2",
            },
            {
                "source_page_id": "paper-1",
                "source_title": "Course Grade Study",
                "Task": "Classification",
                "Student Performance Definition": "Final Grade in Course",
                "Target": "Pass vs Fail",
                "Moment of Prediction": "Week 2",
            },
            {
                "source_page_id": "paper-2",
                "source_title": "Dropout Study",
                "Task": "Classification",
                "Student Performance Definition": "Program dropout",
                "Target": "Dropout vs Program Completion",
                "Moment of Prediction": "End of Course",
            },
            {
                "source_page_id": "paper-3",
                "source_title": "Mixed Study",
                "Task": "Regression",
                "Student Performance Definition": "Final score and program dropout",
                "Target": "Final score and program dropout risk",
                "Moment of Prediction": "During course",
            },
        ],
    }

    summary, detail = build_pred_horizon_task_summary(dfs)

    assert len(summary) == 6
    assert len(detail) == 6

    short_classification = summary[
        (summary["Horizon"] == "Short-term")
        & (summary["Supervised ML Task"] == "Classification")
        & (summary["Target Variable"] == "Pass/fail")
    ].iloc[0]
    long_classification = summary[
        (summary["Horizon"] == "Long-term")
        & (summary["Supervised ML Task"] == "Classification")
        & (summary["Target Variable"] == "Dropout / retention")
    ].iloc[0]
    short_regression = summary[
        (summary["Horizon"] == "Short-term")
        & (summary["Supervised ML Task"] == "Regression")
        & (summary["Target Variable"] == "Dropout / retention")
    ].iloc[0]
    short_regression_grade = summary[
        (summary["Horizon"] == "Short-term")
        & (summary["Supervised ML Task"] == "Regression")
        & (summary["Target Variable"] == "Grade / score / performance")
    ].iloc[0]
    long_regression = summary[
        (summary["Horizon"] == "Long-term")
        & (summary["Supervised ML Task"] == "Regression")
        & (summary["Target Variable"] == "Dropout / retention")
    ].iloc[0]
    long_regression_grade = summary[
        (summary["Horizon"] == "Long-term")
        & (summary["Supervised ML Task"] == "Regression")
        & (summary["Target Variable"] == "Grade / score / performance")
    ].iloc[0]

    assert short_classification["Number of Research Papers"] == 1
    assert short_classification["Papers with early/actionable prediction"] == 1
    assert short_classification["Papers with implemented intervention or deployment"] == 0
    assert "Pass vs Fail" in short_classification["Raw target evidence"]
    assert "Horizon source" in detail.columns
    assert "Raw target evidence" in detail.columns

    assert long_classification["Number of Research Papers"] == 1
    assert long_classification["Papers with early/actionable prediction"] == 0
    assert long_classification["Papers with implemented intervention or deployment"] == 0

    assert short_regression["Number of Research Papers"] == 1
    assert short_regression["Papers with implemented intervention or deployment"] == 1
    assert short_regression_grade["Number of Research Papers"] == 1
    assert long_regression["Number of Research Papers"] == 1
    assert long_regression["Papers with implemented intervention or deployment"] == 1
    assert long_regression_grade["Number of Research Papers"] == 1


def test_write_pred_horizon_task_summary_workbook_from_canonical(tmp_path):
    import json

    canonical_dir = tmp_path / "canonical"
    canonical_dir.mkdir()
    bundle = {
        "provenance": {"source_id": "paper-1"},
        "references": [
            {
                "id": "paper-1",
                "title": "Prediction Study",
                "sync_metadata": {
                    "notion_properties": {
                        "Status": "Accepted For Performance Prediction Task",
                        "Work Nature": "Tested on New Students",
                        "Deployed/ Deployable": "Prototype",
                    }
                },
            }
        ],
        "tasks": [{"id": "task-1", "name": "Performance Prediction"}],
        "reference_tasks": [{"id": "rt-1", "task_id": "task-1"}],
        "task_extractions": [
            {
                "reference_task_id": "rt-1",
                "extracted": [
                    {
                        "Task": "Classification",
                        "Student Performance Definition": "Final Grade",
                        "Target": "Pass vs Fail",
                        "Moment of Prediction": "Week 1",
                    }
                ],
            }
        ],
    }
    (canonical_dir / "paper-1.canonical.json").write_text(json.dumps(bundle), encoding="utf-8")
    output = tmp_path / "summary.xlsx"

    written = write_pred_horizon_task_summary_workbook(canonical_dir, output)

    assert written == output
    result = pd.read_excel(written, sheet_name="target_table")
    assert result.loc[0, "Number of Research Papers"] == 1
    assert pd.ExcelFile(written).sheet_names == ["target_table", "paper_level_detail"]
