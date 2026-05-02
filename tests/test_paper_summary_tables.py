from notion_zotero.analysis.paper_tables import build_paper_summary_tables


class _FakeFrame:
    def __init__(self, rows):
        self._rows = rows

    def to_dict(self, orient):
        assert orient == "records"
        return self._rows


class _BadFrame:
    def to_dict(self, orient):
        raise TypeError("unsupported orient")


def test_paper_summary_tables_merge_duplicate_prediction_rows():
    dfs = {
        "Reading List": [
            {
                "page_id": "paper-1",
                "title": "A Prediction Study",
                "authors": ["Smith et al."],
                "year": "2024",
            }
        ],
        "PRED": [
            {
                "source_page_id": "paper-1",
                "source_title": "A Prediction Study",
                "Context": "Higherr Education",
                "Teaching Method": "Blended LEarning",
                "Data sources": "LMS logs, Student Demographics",
                "Students": "120 students",
                "Courses": "1 programming course",
                "Task": "REgression",
                "Student Performance Definition": "Final Grade in Course",
                "Target": "Final mark",
                "Moment of Prediction": "End of Course",
                "Features": "Gender, Age, LMS clicks",
                "Models": "Random Forest",
                "Assessment Strategy": "10-fold Cross Validation",
                "Performance Metric: Best Model": "RMSE: 0.20 - Random Forest",
            },
            {
                "source_page_id": "paper-1",
                "source_title": "A Prediction Study",
                "Context": "Higher Education",
                "Teaching Method": "Blended Learning",
                "Data sources": "Academic Background",
                "Students": "120 students",
                "Courses": "1 programming course",
                "Task": "Regression",
                "Student Performance Definition": "Final Grade in Course",
                "Target": "Final mark",
                "Moment of Prediction": "End of Course",
                "Features": "Prior GPA",
                "Models": "Random Forest",
                "Assessment Strategy": "10-Fold Cross-Validation",
                "Performance Metric: Best Model": "MAE: 0.15 - Random Forest",
            },
        ],
    }

    tables, audit = build_paper_summary_tables(dfs)

    assert len(tables["PRED"]) == 1
    row = tables["PRED"][0]
    assert row["Study"] == "Smith et al. (2024)"
    assert row["Context"] == "Higher Education"
    assert row["Teaching modality"] == "Blended Learning"
    assert "LMS/VLE/MOOC logs" in row["Data sources"]
    assert "Student demographics/characteristics" in row["Data sources"]
    assert "Academic background records" in row["Data sources"]
    assert row["Prediction task type"] == "Regression"
    assert "Predict the student's final grade" in row["Prediction target / timing"]
    assert "End of Course" in row["Prediction target / timing"]
    assert row["Assessment strategy"] == "K-Fold Cross-Validation"
    assert "Random Forest" in row["Algorithms / models"]
    assert "RMSE=0.20 (Random Forest)" in row["Results"]
    assert "MAE=0.15 (Random Forest)" in row["Results"]
    assert "Limitations" in row
    assert any(item["action"] == "merged_duplicate_extraction_rows" for item in audit)


def test_same_paper_can_have_multiple_distinct_prediction_rows():
    dfs = {
        "Reading List": [
            {
                "page_id": "paper-2",
                "title": "Multi-Outcome Prediction Study",
                "authors": "Santos et al.",
                "year": "2026",
            }
        ],
        "PRED": [
            {
                "source_page_id": "paper-2",
                "Task": "Classification",
                "Student Performance Definition": "Dropout",
                "Target": "Dropout vs No Dropout",
                "Models": "Random Forest",
                "Assessment Strategy": "Holdout Method",
                "Performance Metric: Best Model": "AUC: 0.82 - Random Forest",
            },
            {
                "source_page_id": "paper-2",
                "Task": "Regression",
                "Student Performance Definition": "Final Grade",
                "Target": "Final mark",
                "Models": "SVM",
                "Assessment Strategy": "10-Fold Cross-Validation",
                "Performance Metric: Best Model": "RMSE: 0.20 - SVM",
            },
        ],
    }

    tables, audit = build_paper_summary_tables(dfs)

    assert len(tables["PRED"]) == 2
    assert {row["Prediction task type"] for row in tables["PRED"]} == {
        "Classification",
        "Regression",
    }
    assert any(
        item["action"] == "preserved_distinct_paper_contribution"
        for item in audit
    )


def test_algorithms_features_and_results_use_consistent_display_policy():
    dfs = {
        "Reading List": [
            {"page_id": "paper-3", "title": "Policy Study", "authors": "Ng et al.", "year": "2024"}
        ],
        "PRED": [
            {
                "source_page_id": "paper-3",
                "Task": "Classification",
                "Target": "Pass vs Fail",
                "Models": "RF, SVM, kNN, Logistic Regression, XGBoost",
                "Features": "Gender, Age, GPA, quiz score, LMS clicks, forum posts, course module",
                "Assessment Strategy": "Holdout Method",
                "Performance Metric: Best Model": "{Accuracy: 0.91 - RF, F1-Score: 0.88 - SVM}",
            }
        ],
    }

    tables, _audit = build_paper_summary_tables(dfs)
    row = tables["PRED"][0]

    assert "Random Forest" in row["Algorithms / models"]
    assert "Support Vector Machine" in row["Algorithms / models"]
    assert "k-Nearest Neighbors" in row["Algorithms / models"]
    assert "Demographics" in row["Features"]
    assert "Prior academic performance" in row["Features"]
    assert "LMS activity" in row["Features"]
    assert "Forum / social interaction" in row["Features"]
    assert "Accuracy=0.91 (RF)" in row["Results"]
    assert "F1=0.88 (SVM)" in row["Results"]


def test_paper_summary_tables_sort_by_year_then_study():
    dfs = {
        "Reading List": [
            {"page_id": "paper-b", "title": "Beta Study", "authors": "Beta et al.", "year": "2024"},
            {"page_id": "paper-a", "title": "Alpha Study", "authors": "Alpha et al.", "year": "2024"},
            {"page_id": "paper-old", "title": "Old Study", "authors": "Zeta et al.", "year": "2022"},
        ],
        "PRED": [
            {"source_page_id": "paper-b", "Task": "Regression", "Target": "Grade"},
            {"source_page_id": "paper-a", "Task": "Classification", "Target": "Dropout"},
            {"source_page_id": "paper-old", "Task": "Classification", "Target": "Pass/fail"},
        ],
    }

    tables, _audit = build_paper_summary_tables(dfs)

    assert [row["Study"] for row in tables["PRED"]] == [
        "Zeta et al. (2022)",
        "Alpha et al. (2024)",
        "Beta et al. (2024)",
    ]


def test_paper_summary_tables_build_task_specific_columns():
    dfs = {
        "Reading List": [
            {"page_id": "rec-1", "title": "Recommendation Paper", "authors": "Lee et al.", "year": "2023"},
            {"page_id": "desc-1", "title": "Description Paper", "authors": "Chen et al.", "year": "2022"},
            {"page_id": "kt-1", "title": "KT Paper", "authors": "Wu et al.", "year": "2025"},
        ],
        "REC": [
            {
                "source_page_id": "rec-1",
                "Context": "MOOC",
                "Teaching Method": "Online Learning",
                "Data sources": "Forum posts",
                "Students": "200 learners",
                "Courses": "MOOC course",
                "Target of Recommendation": "Courses to take",
                "Recommender System Type": "Collaborative-Filtering",
                "Initialization Method": (
                    "The approach relies on creating course embeddings; "
                    "RL head and contrastive head use a pre-trained DKT reward signal"
                ),
                "Comments": "Matrix Factorization and IRT models were also compared for benchmarking.",
                "Recommendation types": "Top-10 course recommendations",
                "Evaluation": "Precision@10",
            }
        ],
        "DESC": [
            {
                "source_page_id": "desc-1",
                "Context": "Higher Edfucation",
                "Teaching Method": "E-Learning",
                "Data sources": "Questionnaire",
                "Students": "80 students",
                "Courses": "Chemistry",
                "Task": "Clustering",
                "Models": "k-Means",
                "Theoretical Grounding": "Winne's SRL Model",
                "Implications": "Clusters differed in final grades.",
            }
        ],
        "KT": [
            {
                "source_page_id": "kt-1",
                "Context": "ITS",
                "Teaching Method": "MOOCs",
                "Data sources": "ASSISTments",
                "Students": "500 learners",
                "Courses": "Math",
                "Student Performance Definition": "Next Question Correctedness",
                "Target": "Correct (1) vs Incorrect (0)",
                "Models": "DKT",
                "Assessment Strategy": "Prefix Split",
                "Performance Metric: Best Model": "AUC: 0.80 - DKT",
                "Novelty of Model": "Adds concept embeddings.",
            }
        ],
    }

    tables, audit = build_paper_summary_tables(dfs)

    assert set(tables) == {"ERS", "DESC", "KT"}
    assert tables["ERS"][0]["Recommendation target"] == "Recommend courses or learning paths to students"
    assert tables["ERS"][0]["Recommender type"] == "Collaborative Filtering"
    assert "Learning Embeddings" in tables["ERS"][0]["Algorithms / models"]
    assert "Reinforcement Learning" in tables["ERS"][0]["Algorithms / models"]
    assert "Contrastive Learning" in tables["ERS"][0]["Algorithms / models"]
    assert "Deep Knowledge Tracing" in tables["ERS"][0]["Algorithms / models"]
    assert "Matrix Factorization" in tables["ERS"][0]["Algorithms / models"]
    assert "Item Response Theory" in tables["ERS"][0]["Algorithms / models"]
    assert tables["DESC"][0]["Context"] == "Higher Education"
    assert tables["DESC"][0]["Theoretical grounding"] == "Self-Regulated Learning"
    assert tables["KT"][0]["Context"] == "Intelligent Tutoring System"
    assert tables["KT"][0]["KT target"] == "Predict whether the student will answer the next question correctly"
    assert tables["KT"][0]["Assessment strategy"] == "Temporal Validation"
    assert "Prior-model limitations" in tables["KT"][0]
    assert "New contribution" in tables["KT"][0]
    assert isinstance(audit, list)


def test_paper_summary_tables_accept_dataframe_like_inputs_and_optional_title():
    dfs = {
        "Reading List": _FakeFrame(
            [
                {
                    "page_id": "rec-2",
                    "title": "Fallback Recommendation Paper",
                    "authors": "Garcia et al.",
                }
            ]
        ),
        "REC": _FakeFrame(
            [
                {
                    "source_page_id": "rec-2",
                    "Data sources": "Unknown platform trace",
                    "Teaching Method": "Experimental Studio",
                    "Evaluation": (
                        "This evaluation description is intentionally long. "
                        "It should be shortened for a paper-facing table while "
                        "the raw value remains available in the source table. "
                        "It includes additional methodological detail, repeated "
                        "dataset descriptions, and explanatory notes that are "
                        "too verbose for a compact manuscript table."
                    ),
                }
            ]
        ),
        "MISSING": _BadFrame(),
    }

    tables, audit = build_paper_summary_tables(
        dfs,
        task_tables={"REC": "ERS", "MISSING": "UNKNOWN"},
        include_title=False,
    )

    row = tables["ERS"][0]
    assert row["Study"] == "Garcia et al."
    assert "Paper title" not in row
    assert row["Context"] == ""
    assert "Unknown platform trace" in row["Data sources"]
    assert any(item["action"] == "unmatched_token" for item in audit)
    assert any(item["action"] == "shortened_cell" for item in audit)


def test_paper_summary_tables_use_title_fallback_when_reference_metadata_missing():
    tables, _ = build_paper_summary_tables(
        {
            "REC": [
                {
                    "source_page_id": "missing-reference",
                    "source_title": "Untitled Metadata Paper",
                    "Context": "MOOC",
                }
            ]
        }
    )

    assert tables["ERS"][0]["Study"] == "Untitled Metadata Paper"


def test_paper_summary_dataframe_wrapper_reports_missing_pandas(monkeypatch):
    import builtins
    from notion_zotero.analysis.paper_tables import build_paper_summary_dataframes

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "pandas":
            raise ImportError("pandas blocked for test")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    try:
        build_paper_summary_dataframes({})
    except ImportError as exc:
        assert "pandas is required" in str(exc)
    else:
        raise AssertionError("Expected ImportError")
