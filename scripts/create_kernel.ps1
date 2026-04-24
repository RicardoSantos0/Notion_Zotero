param(
    [string]$VenvPath = ".\.venv"
)

$activate = Join-Path $VenvPath "Scripts\Activate.ps1"
if (Test-Path $activate) {
    Write-Host "Activating virtual environment at $VenvPath..."
    & $activate
    Write-Host "Installing ipykernel kernel 'notion_zotero' using the venv's python..."
    python -m ipykernel install --user --name notion_zotero --display-name "Notion_Zotero (.venv)"
    Write-Host "Kernel 'notion_zotero' installed. Select it in VS Code or Jupyter."
} else {
    Write-Host "Virtual environment not found at '$VenvPath'. Create one first (eg. 'uv venv' or 'python -m venv .venv')."
    exit 1
}
