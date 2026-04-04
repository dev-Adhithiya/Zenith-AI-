# Zenith AI - Local Development Setup
# Run this to set up and run locally

param(
    [switch]$Install,
    [switch]$Run
)

$ErrorActionPreference = "Stop"
$ZenithPath = "..\zenith"

Write-Host "========================================"
Write-Host "Zenith AI - Local Development"
Write-Host "========================================"

if ($Install -or (-not (Test-Path "$ZenithPath\.venv"))) {
    Write-Host "Creating virtual environment..."
    Set-Location $ZenithPath
    python -m venv .venv
    
    Write-Host "Activating virtual environment..."
    .\.venv\Scripts\Activate.ps1
    
    Write-Host "Installing dependencies..."
    pip install --upgrade pip
    pip install -r requirements.txt
    
    Write-Host ""
    Write-Host "Dependencies installed!"
    Write-Host ""
}

if ($Run) {
    Set-Location $ZenithPath
    
    # Check for .env file
    if (-not (Test-Path ".env")) {
        Write-Host "Error: .env file not found"
        Write-Host "Copy .env.example to .env and fill in your values"
        exit 1
    }
    
    Write-Host "Starting Zenith AI server..."
    .\.venv\Scripts\Activate.ps1
    uvicorn main:app --reload --host 0.0.0.0 --port 8000
}

if (-not $Install -and -not $Run) {
    Write-Host "Usage:"
    Write-Host "  .\local-dev.ps1 -Install    # Install dependencies"
    Write-Host "  .\local-dev.ps1 -Run        # Run local server"
    Write-Host "  .\local-dev.ps1 -Install -Run  # Both"
}
