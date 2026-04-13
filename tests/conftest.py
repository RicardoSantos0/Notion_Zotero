from pathlib import Path
import sys

# Prefer installed package import; fall back to adding repository root to sys.path
try:
    import src  # noqa: F401
except Exception:
    ROOT = Path(__file__).resolve().parents[1]
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
