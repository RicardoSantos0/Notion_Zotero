"""Verify schema_registry.yaml is present, parseable, and covers all 6 models."""
import yaml
from pathlib import Path

REGISTRY_PATH = (
    Path(__file__).parent.parent
    / "src"
    / "notion_zotero"
    / "core"
    / "schema_registry.yaml"
)
REQUIRED_MODELS = {
    "Reference", "Task", "ReferenceTask",
    "TaskExtraction", "WorkflowState", "Annotation",
}


def test_registry_exists():
    assert REGISTRY_PATH.exists(), f"schema_registry.yaml not found at {REGISTRY_PATH}"


def test_registry_parses():
    data = yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    assert "models" in data
    assert "version" in data


def test_registry_covers_all_models():
    data = yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8"))
    present = set(data["models"].keys())
    missing = REQUIRED_MODELS - present
    assert not missing, f"Models missing from registry: {missing}"


def test_every_field_has_owner_and_required():
    data = yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8"))
    problems = []
    for model_name, model_data in data["models"].items():
        assert "fields" in model_data, f"{model_name} has no 'fields' section"
        for field_name, field_meta in model_data["fields"].items():
            if "owner" not in field_meta:
                problems.append(f"{model_name}.{field_name}: missing 'owner'")
            if "required" not in field_meta:
                problems.append(f"{model_name}.{field_name}: missing 'required'")
    assert not problems, "Registry field metadata problems:\n" + "\n".join(problems)


def test_owners_are_valid_values():
    data = yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8"))
    valid = {"zotero", "notion", "system"}
    problems = []
    for model_name, model_data in data["models"].items():
        for field_name, field_meta in model_data["fields"].items():
            owner = field_meta.get("owner")
            if owner not in valid:
                problems.append(
                    f"{model_name}.{field_name}: invalid owner {owner!r} "
                    f"(must be one of {valid})"
                )
    assert not problems, "\n".join(problems)
