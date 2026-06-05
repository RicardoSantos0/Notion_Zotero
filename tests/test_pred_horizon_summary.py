import pytest

pd = pytest.importorskip("pandas")

from notion_zotero.analysis.pred_horizon_summary import (
    build_pred_horizon_task_summary,
    classify_horizons,
    classify_horizons_with_source,
    classify_supervised_ml_task,
    classify_target_variable,
    classify_target_variables,
    find_unclassified_pred_horizon_rows,
    has_at_risk_framing,
    has_implemented_intervention_or_deployment,
    is_early_actionable_prediction,
    write_pred_horizon_task_summary_workbook,
    STRONG_LONG_TERM_OVERRIDE_PATTERNS,
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
    assert classify_target_variable(short_row) == "Course Grade"
    assert classify_target_variable(long_row) == "Dropout"
    assert classify_target_variable(
        {"Student Performance Definition": "Quality of next interaction"}
    ) == "Next Interaction / Question Outcome"
    assert classify_target_variable(
        {"Student Performance Definition": "Close to Pass Scores"}
    ) == "Course Grade"
    assert classify_target_variable(
        {"Target": "Final Grade in Course"}
    ) == "Course Grade"
    assert classify_target_variable(
        {"Target": "Exam Score (0 to 100)"}
    ) == "Exam Score"
    assert classify_target_variable(
        {"Target": "Assessment Score (0-100)"}
    ) == "Assessment"
    assert classify_target_variable(
        {"Target": "Grade Point Average"}
    ) == "GPA"
    assert classify_target_variable(
        {"Student Performance Definition": "Final Exam Grade", "Target": "Pass vs Fail"}
    ) == "Exam Grade"
    assert classify_target_variable(
        {"Student Performance Definition": "Lab Assessment", "Target": "Pass vs Fail"}
    ) == "Assessment"
    assert classify_target_variable(
        {"Student Performance Definition": "Academic success"}
    ) == "Learning outcome / skill"
    assert classify_target_variables(
        {
            "Student Performance Definition": "Final score and program dropout",
            "Target": "Final score and program dropout risk",
        }
    ) == ["Dropout"]
    assert classify_target_variable(
        {"Target": "At-Risk (1) vs Not At-Risk (0)"}
    ) == "Other / ambiguous"
    assert has_at_risk_framing({"Target": "At-Risk (1) vs Not At-Risk (0)"}) is True
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


def test_new_target_categories_cover_previously_ambiguous_strings():
    # At-risk / performance-tier labels are framing flags, not target variables.
    assert classify_target_variable({"Target": "Top 60% vs Bottom 40%"}) == "Other / ambiguous"
    assert classify_target_variable({"Target": "Above Median / Below Median"}) == "Other / ambiguous"
    assert classify_target_variable({"Target": "At-risk, Sufficient, Average, Good, Excellent"}) == "Other / ambiguous"
    assert classify_target_variable({"Target": "Top 20% (1) vs not 20% (0)"}) == "Other / ambiguous"
    assert has_at_risk_framing({"Target": "Top 60% vs Bottom 40%"}) is True
    assert has_at_risk_framing({"Target": "Above Median / Below Median"}) is True

    # Learning outcome / skill
    assert classify_target_variable({"Target": "Cognitive Skills"}) == "Learning outcome / skill"
    assert classify_target_variable({"Target": "Recall Rate on student-word sessions"}) == "Learning outcome / skill"
    assert classify_target_variable({"Target": "Low vs High learning gains"}) == "Learning outcome / skill"

    # Time to completion
    assert classify_target_variable({"Target": "Time to Degree"}) == "Time to completion"
    assert classify_target_variable({"Target": "Years to Degree"}) == "Time to completion"

    # Continue (1) vs Not Continue (0) -> Dropout
    assert classify_target_variable({"Target": "Continue (1) vs Not Continue (0)"}) == "Dropout"

    # Close to Fail / Pass -> Course Grade
    assert classify_target_variable({"Target": "Close to Fail (1) vs not (0)"}) == "Course Grade"
    assert classify_target_variable({"Target": "Close to Pass (1) vs not (0)"}) == "Course Grade"

    # Delay vs Timely Submission -> Assessment submission outcome.
    assert classify_target_variable({"Target": "Delay vs Timely Submission"}) == "Assessment"


def test_reviewed_target_overrides_match_manual_audit_decisions():
    examples = [
        ({"Student Performance Definition": "Grade Range", "Target": "A, B, C and F"}, "Course Grade"),
        ({"Student Performance Definition": "AP Score", "Target": "Performance Clusters: A to E"}, "AP Score"),
        ({"Student Performance Definition": "Student will Complete Degree", "Target": "True vs False"}, "Graduation"),
        ({"Student Performance Definition": "Probability of Failing an Upcoming Assessment", "Target": "Failing (1) vs Succeeding (0)"}, "Assessment"),
        ({"Student Performance Definition": "Delay in Submission", "Target": "Number of Days of Delay"}, "Delivery past the Deadline"),
        ({"Student Performance Definition": "Obtaining a top 20% GPA on a MSc program", "Target": "Top 20% (1) vs not 20% (0)"}, "GPA"),
        ({"Student Performance Definition": "Student graduates or Drops out", "Target": "Graduated (0) vs Dropped out (1)"}, "Graduation"),
        ({"Student Performance Definition": "Performance Groups", "Target": "Low, Medium, High"}, "Exam Score"),
        ({"Student Performance Definition": "End of Program Graduation or Dropout", "Target": "Dropped out (0) vs Graduated (1)"}, "Graduation"),
        ({"Student Performance Definition": "End of Program Mark", "Target": "End of Program Passing Mark (A to E)"}, "GPA"),
        ({"Student Performance Definition": "Trend of GPA from Previous Semester", "Target": "High (1) vs Low (0)"}, "GPA trend"),
        ({"Student Performance Definition": "Dropout", "Target": "At-risk (1) vs Not at-risk (0)"}, "Dropout"),
        ({"Student Performance Definition": "Summative Assessment Results", "Target": "Below 50% (0) vs Above (1)"}, "Exam Grade"),
        ({"Student Performance Definition": "To X% GPA", "Target": "Excellent vs Good vs Poor"}, "GPA"),
        ({"Student Performance Definition": "Student Graduation in Expected Time", "Target": "Success vs Fail"}, "Graduation"),
        ({"Student Performance Definition": "Academic Performance", "Target": "Grade"}, "Course Grade"),
        ({"Student Performance Definition": "Post-Test Scores", "Target": "High (1) vs Low(0)"}, "Assessment Grade"),
    ]

    for row, expected in examples:
        assert classify_target_variable(row) == expected


def test_horizon_long_term_suppresses_short_term_on_strong_signals():
    # "course" appears incidentally but graduation dominates → Long-term only
    assert classify_horizons(
        {"Student Performance Definition": "Graduation from the course of study", "Target": "Graduate vs Not Graduate"}
    ) == ["Long-term"]

    # retention + course mention → Long-term only
    assert classify_horizons(
        {"Student Performance Definition": "Student retention over course of degree", "Target": "Retained vs Dropout"}
    ) == ["Long-term"]

    # No strong long-term signal → Both kept
    assert classify_horizons(
        {"Student Performance Definition": "Final score and program dropout", "Target": "Final score and program dropout risk"}
    ) == ["Short-term", "Long-term"]

    # Genuine course-level: no suppression
    assert classify_horizons(
        {"Student Performance Definition": "Final Grade in Course", "Target": "Pass vs Fail"}
    ) == ["Short-term"]


def test_course_field_fallback_handles_empty_primary_target_fields():
    row = {
        "Student Performance Definition": "",
        "Target": "",
        "Courses": "Introductory Programming",
    }
    assert classify_horizons_with_source(row) == [
        ("Short-term", "course-level context (Courses field; empty primary fields)")
    ]

    program_row = {
        "Student Performance Definition": "",
        "Target": "",
        "Courses": "Software Engineering Program",
    }
    assert classify_horizons(program_row) == ["Long-term"]


def test_early_actionable_covers_semester_and_year_level_timing():
    # semester-level timing is early for program-level graduation prediction
    assert is_early_actionable_prediction({"Moment of Prediction": "At semester end"}) is True
    assert is_early_actionable_prediction({"Moment of Prediction": "During first semester"}) is True
    assert is_early_actionable_prediction({"Moment of Prediction": "After first year"}) is True
    assert is_early_actionable_prediction({"Moment of Prediction": "End of second year"}) is True
    # True post-course/program markers remain False
    assert is_early_actionable_prediction({"Moment of Prediction": "After graduation"}) is False
    assert is_early_actionable_prediction({"Moment of Prediction": "End of Program"}) is False


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

    assert len(summary) == 4
    assert len(detail) == 4

    short_classification = summary[
        (summary["Horizon"] == "Short-term")
        & (summary["Supervised ML Task"] == "Classification")
            & (summary["Target Variable"] == "Course Grade")
    ].iloc[0]
    long_classification = summary[
        (summary["Horizon"] == "Long-term")
        & (summary["Supervised ML Task"] == "Classification")
            & (summary["Target Variable"] == "Dropout")
    ].iloc[0]
    short_regression = summary[
        (summary["Horizon"] == "Short-term")
        & (summary["Supervised ML Task"] == "Regression")
            & (summary["Target Variable"] == "Dropout")
    ].iloc[0]
    long_regression = summary[
        (summary["Horizon"] == "Long-term")
        & (summary["Supervised ML Task"] == "Regression")
            & (summary["Target Variable"] == "Dropout")
    ].iloc[0]

    assert short_classification["Number of Research Papers"] == 1
    assert short_classification["Papers with early/actionable prediction"] == 1
    assert short_classification["Papers with implemented intervention or deployment"] == 0
    assert "Pass vs Fail" in short_classification["Raw target evidence"]
    assert "Horizon source" in detail.columns
    assert "Raw target evidence" in detail.columns
    assert "At-risk / tier framing" in detail.columns
    assert "Papers with at-risk / tier framing" in summary.columns

    assert long_classification["Number of Research Papers"] == 1
    assert long_classification["Papers with early/actionable prediction"] == 0
    assert long_classification["Papers with implemented intervention or deployment"] == 0

    assert short_regression["Number of Research Papers"] == 1
    assert short_regression["Papers with implemented intervention or deployment"] == 1
    assert long_regression["Number of Research Papers"] == 1
    assert long_regression["Papers with implemented intervention or deployment"] == 1


def test_unclassified_horizon_audit_uses_pred_rows_only_and_course_fallback():
    dfs = {
        "Reading List": [
            {"page_id": "paper-1", "title": "Single Course Study"},
            {"page_id": "paper-2", "title": "Generic Dropout Study"},
        ],
        "PRED": [
            {
                "source_page_id": "paper-1",
                "source_title": "Single Course Study",
                "Task": "Classification",
                "Student Performance Definition": "",
                "Target": "",
                "Courses": "Mathematics",
            },
            {
                "source_page_id": "paper-2",
                "source_title": "Generic Dropout Study",
                "Task": "Classification",
                "Student Performance Definition": "Dropout",
                "Target": "Dropout vs No Dropout",
            },
        ],
        "KT": [
            {
                "source_page_id": "paper-3",
                "Task": "Classification",
                "Student Performance Definition": "",
                "Target": "Correct / Incorrect",
            }
        ],
    }

    unclassified = find_unclassified_pred_horizon_rows(dfs)

    assert len(unclassified) == 1
    assert unclassified.iloc[0]["Paper title"] == "Generic Dropout Study"


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
