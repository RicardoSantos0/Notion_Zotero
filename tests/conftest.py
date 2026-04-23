from pathlib import Path
import sys

import pytest

# Prefer installed package import; fall back to adding repository root to sys.path
try:
    import src  # noqa: F401
except Exception:
    ROOT = Path(__file__).resolve().parents[1]
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))


@pytest.fixture
def valid_provenance() -> dict:
    """Minimal provenance dict satisfying the TP-006 completeness validator."""
    return {
        "source_id": "test",
        "domain_pack_id": "test-pack",
        "domain_pack_version": "0.0.1",
    }
