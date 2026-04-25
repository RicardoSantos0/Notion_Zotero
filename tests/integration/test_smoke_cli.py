import sys
import subprocess
import pytest

pytestmark = pytest.mark.integration


def test_cli_help_runs():
    # Run the package CLI module and ensure it exits successfully and prints usage/help
    res = subprocess.run([sys.executable, "-m", "notion_zotero.cli", "--help"], capture_output=True, text=True)
    assert res.returncode == 0
    out = (res.stdout or "") + (res.stderr or "")
    assert "positional arguments" in out or "usage" in out.lower()
