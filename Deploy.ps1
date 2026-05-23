<#
.SYNOPSIS
    Builds the Sinking Funds Manager into a standalone executable.
#>
Write-Host "Installing requirements..." -ForegroundColor Cyan
pip install pyinstaller PyQt6

Write-Host "`nBuilding Sinking Funds Manager..." -ForegroundColor Cyan
# The --add-data flag ensures the icon.svg is bundled with the executable so the window icon still loads.
python -m PyInstaller --noconsole --windowed --name="Sinking Funds Manager" --add-data "icon.svg;." main.py

Write-Host "`n=======================================================" -ForegroundColor Green
Write-Host "Build complete!" -ForegroundColor Green
Write-Host "You can find your compiled application inside the 'dist' folder." -ForegroundColor Green
Write-Host "=======================================================" -ForegroundColor Green

Read-Host -Prompt "Press Enter to exit"
