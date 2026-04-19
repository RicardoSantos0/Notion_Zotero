"""A small set of reusable, generic extraction templates."""
from __future__ import annotations

from .base import ExtractionTemplate, ColumnDefinition


prediction_modeling = ExtractionTemplate(
    template_id="prediction_modeling",
    display_name="Prediction / Modeling",
    expected_columns=[
        ColumnDefinition("Metric", aliases=["metric", "score"], required=True),
        ColumnDefinition("Value", aliases=["value", "score_value"], required=True),
    ],
)

descriptive_analysis = ExtractionTemplate(
    template_id="descriptive_analysis",
    display_name="Descriptive Analysis",
    expected_columns=[
        ColumnDefinition("Measure", aliases=["measure", "stat"], required=True),
        ColumnDefinition("Value", aliases=["value", "mean", "median"], required=True),
    ],
)

recommendation_system = ExtractionTemplate(
    template_id="recommendation_system",
    display_name="Recommender System Results",
    expected_columns=[
        ColumnDefinition("Algorithm", aliases=["model", "approach"], required=True),
        ColumnDefinition("Metric", aliases=["metric", "score"], required=True),
    ],
)

sequence_tracing = ExtractionTemplate(
    template_id="sequence_tracing",
    display_name="Sequence / Tracing",
    expected_columns=[ColumnDefinition("Event", aliases=["event", "step"], required=True)],
)

generic_systematic_review = ExtractionTemplate(
    template_id="generic_systematic_review",
    display_name="Generic Systematic Review",
    expected_columns=[ColumnDefinition("Field", aliases=["field", "attribute"], required=False)],
)


summary_table = ExtractionTemplate(
    template_id="summary_table",
    display_name="Summary Table",
    expected_columns=[
        ColumnDefinition("Key", aliases=["key", "item"], required=False),
        ColumnDefinition("Value", aliases=["value", "notes"], required=False),
    ],
)

methods_table = ExtractionTemplate(
    template_id="methods_table",
    display_name="Methods Table",
    expected_columns=[
        ColumnDefinition("Method", aliases=["method", "approach"], required=True),
        ColumnDefinition("Description", aliases=["description", "desc"], required=False),
    ],
)

dataset_table = ExtractionTemplate(
    template_id="dataset_table",
    display_name="Dataset Table",
    expected_columns=[
        ColumnDefinition("Dataset", aliases=["dataset", "sample"], required=True),
        ColumnDefinition("N", aliases=["n", "size"], required=False),
    ],
)

findings_table = ExtractionTemplate(
    template_id="findings_table",
    display_name="Findings Table",
    expected_columns=[
        ColumnDefinition("Measure", aliases=["measure", "metric"], required=True),
        ColumnDefinition("Value", aliases=["value", "result"], required=True),
    ],
)

conclusions_table = ExtractionTemplate(
    template_id="conclusions_table",
    display_name="Conclusions Table",
    expected_columns=[ColumnDefinition("Conclusion", aliases=["conclusion", "takeaway"], required=False)],
)

metrics_table = ExtractionTemplate(
    template_id="metrics_table",
    display_name="Metrics Table",
    expected_columns=[
        ColumnDefinition("Metric", aliases=["metric", "score"], required=True),
        ColumnDefinition("Value", aliases=["value", "score_value"], required=True),
    ],
)

population_table = ExtractionTemplate(
    template_id="population_table",
    display_name="Population / Sample Table",
    expected_columns=[
        ColumnDefinition("Participant", aliases=["participant", "participants", "sample"], required=False),
        ColumnDefinition("N", aliases=["n", "size"], required=False),
    ],
)

limitations_table = ExtractionTemplate(
    template_id="limitations_table",
    display_name="Limitations Table",
    expected_columns=[ColumnDefinition("Limitation", aliases=["limitation", "weakness"], required=False)],
)

TEMPLATES = {
    prediction_modeling.template_id: prediction_modeling,
    descriptive_analysis.template_id: descriptive_analysis,
    recommendation_system.template_id: recommendation_system,
    sequence_tracing.template_id: sequence_tracing,
    generic_systematic_review.template_id: generic_systematic_review,
    summary_table.template_id: summary_table,
    methods_table.template_id: methods_table,
    dataset_table.template_id: dataset_table,
    findings_table.template_id: findings_table,
    conclusions_table.template_id: conclusions_table,
    metrics_table.template_id: metrics_table,
    population_table.template_id: population_table,
    limitations_table.template_id: limitations_table,
}

__all__ = ["TEMPLATES", "prediction_modeling", "descriptive_analysis"]
