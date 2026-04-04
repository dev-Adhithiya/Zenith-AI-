# Zenith AI - Setup Secrets in GCP Secret Manager
# Run this BEFORE deploying to Cloud Run

param(
    [Parameter(Mandatory=$true)]
    [string]$ProjectId,
    
    [Parameter(Mandatory=$true)]
    [string]$GoogleClientId,
    
    [Parameter(Mandatory=$true)]
    [string]$GoogleClientSecret,
    
    [string]$JwtSecretKey
)

$ErrorActionPreference = "Stop"

Write-Host "========================================"
Write-Host "Zenith AI - Secret Manager Setup"
Write-Host "========================================"

# Generate JWT secret if not provided
if (-not $JwtSecretKey) {
    $JwtSecretKey = -join ((65..90) + (97..122) + (48..57) | Get-Random -Count 64 | ForEach-Object {[char]$_})
    Write-Host "Generated JWT Secret Key"
}

# Set project
gcloud config set project $ProjectId

# Enable Secret Manager API
Write-Host "Enabling Secret Manager API..."
gcloud services enable secretmanager.googleapis.com

# Create secrets
Write-Host "Creating secrets..."

# Function to create or update secret
function Set-GcpSecret {
    param(
        [string]$Name,
        [string]$Value
    )
    
    # Check if secret exists
    $exists = gcloud secrets list --filter="name:$Name" --format="value(name)" 2>$null
    
    if ($exists) {
        Write-Host "Updating secret: $Name"
        $Value | gcloud secrets versions add $Name --data-file=-
    } else {
        Write-Host "Creating secret: $Name"
        $Value | gcloud secrets create $Name --data-file=-
    }
}

Set-GcpSecret -Name "google-client-id" -Value $GoogleClientId
Set-GcpSecret -Name "google-client-secret" -Value $GoogleClientSecret
Set-GcpSecret -Name "jwt-secret-key" -Value $JwtSecretKey

# Grant Cloud Run service account access to secrets
Write-Host "Granting Cloud Run access to secrets..."
$ProjectNumber = gcloud projects describe $ProjectId --format="value(projectNumber)"
$ServiceAccount = "$ProjectNumber-compute@developer.gserviceaccount.com"

$secrets = @("google-client-id", "google-client-secret", "jwt-secret-key")
foreach ($secret in $secrets) {
    gcloud secrets add-iam-policy-binding $secret `
        --member="serviceAccount:$ServiceAccount" `
        --role="roles/secretmanager.secretAccessor" `
        --quiet
}

Write-Host "========================================"
Write-Host "Secrets Setup Complete!"
Write-Host "========================================"
Write-Host ""
Write-Host "Secrets created:"
foreach ($secret in $secrets) {
    Write-Host "  - $secret"
}
Write-Host ""
Write-Host "Service account granted access: $ServiceAccount"
Write-Host ""
Write-Host "You can now run deploy.ps1 to deploy to Cloud Run"
Write-Host "========================================"
