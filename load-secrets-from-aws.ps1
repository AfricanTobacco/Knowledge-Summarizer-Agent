# Load secrets from AWS Secrets Manager and create .env file
# This script retrieves secrets from AWS and populates the .env file

param(
    [string]$Region = "us-west-2",
    [string]$OutputFile = ".env"
)

Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host "="*79 -ForegroundColor Cyan
Write-Host "Knowledge Summarizer Agent - Load Secrets from AWS" -ForegroundColor Cyan
Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host "="*79 -ForegroundColor Cyan
Write-Host ""

# Check if AWS CLI is installed
try {
    aws --version | Out-Null
} catch {
    Write-Host "❌ AWS CLI not found. Please install it first." -ForegroundColor Red
    exit 1
}

# Check AWS credentials
Write-Host "🔍 Checking AWS credentials..." -ForegroundColor Yellow
try {
    $identity = aws sts get-caller-identity --region $Region | ConvertFrom-Json
    Write-Host "✅ AWS credentials valid: $($identity.Arn)" -ForegroundColor Green
} catch {
    Write-Host "❌ AWS credentials not configured. Run 'aws configure' first." -ForegroundColor Red
    exit 1
}

Write-Host ""

# Function to get secret value
function Get-AWSSecretValue {
    param(
        [string]$SecretName
    )

    try {
        $secretJson = aws secretsmanager get-secret-value --secret-id $SecretName --region $Region --query SecretString --output text 2>$null
        if ($LASTEXITCODE -eq 0) {
            return $secretJson | ConvertFrom-Json
        } else {
            Write-Host "⚠️  Secret not found: $SecretName" -ForegroundColor Yellow
            return $null
        }
    } catch {
        Write-Host "⚠️  Error retrieving secret: $SecretName" -ForegroundColor Yellow
        return $null
    }
}

# Retrieve all secrets
Write-Host "📥 Retrieving secrets from AWS Secrets Manager..." -ForegroundColor Yellow
Write-Host ""

$slack = Get-AWSSecretValue -SecretName "knowledge-summarizer-slack"
$notion = Get-AWSSecretValue -SecretName "knowledge-summarizer-notion"
$gcp = Get-AWSSecretValue -SecretName "knowledge-summarizer-gcp-service-account"
$pinecone = Get-AWSSecretValue -SecretName "knowledge-summarizer-pinecone"
$openai = Get-AWSSecretValue -SecretName "knowledge-summarizer-openai"
$anthropic = Get-AWSSecretValue -SecretName "knowledge-summarizer-anthropic"

# Build .env content
$envContent = @"
# Knowledge Summarizer Agent - Environment Variables
# Auto-generated from AWS Secrets Manager on $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
# Region: $Region

# ============================================================================
# SLACK API CONFIGURATION
# ============================================================================
SLACK_BOT_TOKEN=$($slack.slack_bot_token)
SLACK_APP_TOKEN=$($slack.slack_app_token)
SLACK_SIGNING_SECRET=$($slack.slack_signing_secret)
SLACK_WORKSPACE_ID=your-workspace-id

# ============================================================================
# NOTION API CONFIGURATION
# ============================================================================
NOTION_API_KEY=$($notion.notion_api_key)
NOTION_DATABASE_ID=$($notion.notion_database_id)

# ============================================================================
# GOOGLE DRIVE API CONFIGURATION
# ============================================================================
GOOGLE_APPLICATION_CREDENTIALS=./credentials/google-service-account.json
GOOGLE_DRIVE_FOLDER_ID=your-folder-id

# ============================================================================
# PINECONE VECTOR DATABASE
# ============================================================================
PINECONE_API_KEY=$($pinecone.pinecone_api_key)
PINECONE_ENVIRONMENT=$($pinecone.pinecone_environment)
PINECONE_INDEX_NAME=$($pinecone.pinecone_index_name)

# ============================================================================
# AWS CONFIGURATION
# ============================================================================
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
AWS_REGION=$Region

# ============================================================================
# GCP CONFIGURATION
# ============================================================================
GCP_PROJECT_ID=your-gcp-project-id
GCP_REGION=us-central1

# ============================================================================
# OPENAI API (for embeddings)
# ============================================================================
OPENAI_API_KEY=$($openai.openai_api_key)

# ============================================================================
# ANTHROPIC API (for summarization)
# ============================================================================
ANTHROPIC_API_KEY=$($anthropic.anthropic_api_key)

# ============================================================================
# DATA AUDIT SETTINGS
# ============================================================================
PII_DETECTION_ENABLED=true
ANONYMIZE_SAMPLE_DATA=true
MAX_SAMPLE_SIZE=500

# ============================================================================
# COMPLIANCE SETTINGS
# ============================================================================
DATA_RETENTION_DAYS=90
POPIA_COMPLIANCE_MODE=strict
LOG_LEVEL=INFO

# ============================================================================
# COST MONITORING
# ============================================================================
MONTHLY_BUDGET_USD=50
ALERT_THRESHOLD_PERCENT=80
"@

# Write .env file
$envContent | Out-File -FilePath $OutputFile -Encoding UTF8

# Save GCP service account key to file
if ($gcp) {
    $credentialsDir = "credentials"
    if (!(Test-Path $credentialsDir)) {
        New-Item -ItemType Directory -Path $credentialsDir | Out-Null
    }

    $gcpKeyPath = "$credentialsDir/google-service-account.json"
    $gcp | ConvertTo-Json -Depth 10 | Out-File -FilePath $gcpKeyPath -Encoding UTF8
    Write-Host "✅ Saved GCP service account key to: $gcpKeyPath" -ForegroundColor Green
}

Write-Host ""
Write-Host "=" -NoNewline -ForegroundColor Green
Write-Host "="*79 -ForegroundColor Green
Write-Host "✅ SECRETS LOADED SUCCESSFULLY" -ForegroundColor Green
Write-Host "=" -NoNewline -ForegroundColor Green
Write-Host "="*79 -ForegroundColor Green
Write-Host ""

Write-Host "Generated .env file: $OutputFile" -ForegroundColor Cyan
Write-Host ""

Write-Host "Retrieved secrets:" -ForegroundColor Yellow
if ($slack) { Write-Host "  ✅ Slack credentials" -ForegroundColor Green } else { Write-Host "  ❌ Slack credentials" -ForegroundColor Red }
if ($notion) { Write-Host "  ✅ Notion credentials" -ForegroundColor Green } else { Write-Host "  ❌ Notion credentials" -ForegroundColor Red }
if ($gcp) { Write-Host "  ✅ GCP service account" -ForegroundColor Green } else { Write-Host "  ❌ GCP service account" -ForegroundColor Red }
if ($pinecone) { Write-Host "  ✅ Pinecone credentials" -ForegroundColor Green } else { Write-Host "  ❌ Pinecone credentials" -ForegroundColor Red }
if ($openai) { Write-Host "  ✅ OpenAI credentials" -ForegroundColor Green } else { Write-Host "  ❌ OpenAI credentials" -ForegroundColor Red }
if ($anthropic) { Write-Host "  ✅ Anthropic credentials" -ForegroundColor Green } else { Write-Host "  ❌ Anthropic credentials" -ForegroundColor Red }

Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Review the .env file: cat $OutputFile" -ForegroundColor White
Write-Host "  2. Update any remaining placeholders (workspace IDs, folder IDs, etc.)" -ForegroundColor White
Write-Host "  3. Test API connections: python scripts/export_samples.py" -ForegroundColor White
Write-Host ""

Write-Host "⚠️  Security reminder:" -ForegroundColor Yellow
Write-Host "  • Never commit the .env file to git (already in .gitignore)" -ForegroundColor White
Write-Host "  • Rotate secrets every 90 days" -ForegroundColor White
Write-Host "  • Keep AWS credentials secure" -ForegroundColor White
Write-Host ""
