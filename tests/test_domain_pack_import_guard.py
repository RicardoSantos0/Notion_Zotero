"""CI guard: domain pack files must not import from notion_zotero.core."""
import ast
from pathlib import Path


def test_domain_packs_no_core_imports():
    domain_pack_dir = (
        Path(__file__).parent.parent
        / "src"
        / "notion_zotero"
        / "schemas"
        / "domain_packs"
    )
    violations = []

    for py_file in sorted(domain_pack_dir.glob("*.py")):
        if py_file.name.startswith("_"):
            continue
        source = py_file.read_text(encoding="utf-8")
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                if "notion_zotero.core" in node.module:
                    violations.append(
                        f"{py_file.name}: imports from {node.module!r}"
                    )
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if "notion_zotero.core" in alias.name:
                        violations.append(
                            f"{py_file.name}: imports {alias.name!r}"
                        )

    assert not violations, (
        "Domain pack import violations found (domain packs must not import from "
        "notion_zotero.core):\n" + "\n".join(violations)
    )
