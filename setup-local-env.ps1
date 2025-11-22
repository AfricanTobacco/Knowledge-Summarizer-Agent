# Setup local .env file for development
# This script helps you create a .env file without using AWS Secrets Manager

Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host "="*79 -ForegroundColor Cyan
Write-Host "Knowledge Summarizer Agent - Local Environment Setup" -ForegroundColor Cyan
Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host "="*79 -ForegroundColor Cyan
Write-Host ""

Write-Host "This script will help you create a .env file for local development." -ForegroundColor Yellow
Write-Host "You can press Enter to skip optional fields." -ForegroundColor Yellow
Write-Host ""

# Check if .env already exists
if (Test-Path ".env") {
    $overwrite = Read-Host ".env file already exists. Overwrite? (y/N)"
    if ($overwrite -ne "y" -and $overwrite -ne "Y") {
        Write-Host "❌ Cancelled. Existing .env file preserved." -ForegroundColor Yellow
        exit 0
    }
    Write-Host ""
}

# Collect credentials
Write-Host "1️⃣  SLACK CREDENTIALS" -ForegroundColor Cyan
Write-Host "   See: docs/API_SETUP.md#1-slack-api-setup" -ForegroundColor Gray
$slackBotToken = Read-Host "   Slack Bot Token (xoxb-...)"
$slackAppToken = Read-Host "   Slack App Token (xapp-...)"
$slackSigningSecret = Read-Host "   Slack Signing Secret"
$slackWorkspaceId = Read-Host "   Slack Workspace ID (optional)"
Write-Host ""

Write-Host "2️⃣  NOTION CREDENTIALS" -ForegroundColor Cyan
Write-Host "   See: docs/API_SETUP.md#2-notion-api-setup" -ForegroundColor Gray
$notionApiKey = Read-Host "   Notion API Key (secret_...)"
$notionDatabaseId = Read-Host "   Notion Database ID (optional)"
Write-Host ""

Write-Host "3️⃣  GOOGLE DRIVE CREDENTIALS" -ForegroundColor Cyan
Write-Host "   See: docs/API_SETUP.md#3-google-drive-api-setup" -ForegroundColor Gray
$gcpKeyPath = Read-Host "   Path to GCP service account JSON file"
$driveFolderId = Read-Host "   Google Drive Folder ID (optional)"
Write-Host ""

Write-Host "4️⃣  PINECONE CREDENTIALS" -ForegroundColor Cyan
Write-Host "   See: docs/API_SETUP.md#4-pinecone-setup" -ForegroundColor Gray
$pineconeApiKey = Read-Host "   Pinecone API Key"
$pineconeEnvironment = Read-Host "   Pinecone Environment (e.g., us-west1-gcp)"
$pineconeIndexName = Read-Host "   Pinecone Index Name (default: knowledge-summarizer)"
if ([string]::IsNullOrEmpty($pineconeIndexName)) {
    $pineconeIndexName = "knowledge-summarizer"
}
Write-Host ""

Write-Host "5️⃣  OPENAI CREDENTIALS" -ForegroundColor Cyan
Write-Host "   See: docs/API_SETUP.md#5-openai-api-setup" -ForegroundColor Gray
$openaiApiKey = Read-Host "   OpenAI API Key (sk-...)"
Write-Host ""

Write-Host "6️⃣  ANTHROPIC CREDENTIALS" -ForegroundColor Cyan
Write-Host "   See: docs/API_SETUP.md#6-anthropic-api-setup" -ForegroundColor Gray
$anthropicApiKey = Read-Host "   Anthropic API Key (sk-ant-...)"
Write-Host ""

# Copy GCP service account key if provided
if ($gcpKeyPath -and (Test-Path $gcpKeyPath)) {
    $credentialsDir = "credentials"
    if (!(Test-Path $credentialsDir)) {
        New-Item -ItemType Directory -Path $credentialsDir | Out-Null
    }

    Copy-Item $gcpKeyPath "$credentialsDir/google-service-account.json"
    Write-Host "✅ Copied GCP service account key to credentials/" -ForegroundColor Green
    $gcpCredPath = "./credentials/google-service-account.json"
} else {
    $gcpCredPath = "./credentials/google-service-account.json"
}

# Build .env content
$envContent = @"
# Knowledge Summarizer Agent - Environment Variables
# Created: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
# For local development

# ============================================================================
# SLACK API CONFIGURATION
# ============================================================================
SLACK_BOT_TOKEN=$slackBotToken
SLACK_APP_TOKEN=$slackAppToken
SLACK_SIGNING_SECRET=$slackSigningSecret
SLACK_WORKSPACE_ID=$slackWorkspaceId

# ============================================================================
# NOTION API CONFIGURATION
# ============================================================================
NOTION_API_KEY=$notionApiKey
NOTION_DATABASE_ID=$notionDatabaseId

# ============================================================================
# GOOGLE DRIVE API CONFIGURATION
# ============================================================================
GOOGLE_APPLICATION_CREDENTIALS=$gcpCredPath
GOOGLE_DRIVE_FOLDER_ID=$driveFolderId

# ============================================================================
# PINECONE VECTOR DATABASE
# ============================================================================
PINECONE_API_KEY=$pineconeApiKey
PINECONE_ENVIRONMENT=$pineconeEnvironment
PINECONE_INDEX_NAME=$pineconeIndexName

# ============================================================================
# AWS CONFIGURATION (for production deployment)
# ============================================================================
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
AWS_REGION=us-west-2

# ============================================================================
# GCP CONFIGURATION (for production deployment)
# ============================================================================
GCP_PROJECT_ID=your-gcp-project-id
GCP_REGION=us-central1

# ============================================================================
# OPENAI API (for embeddings)
# ============================================================================
OPENAI_API_KEY=$openaiApiKey

# ============================================================================
# ANTHROPIC API (for summarization)
# ============================================================================
ANTHROPIC_API_KEY=$anthropicApiKey

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
$envContent | Out-File -FilePath ".env" -Encoding UTF8

Write-Host ""
Write-Host "=" -NoNewline -ForegroundColor Green
Write-Host "="*79 -ForegroundColor Green
Write-Host "✅ LOCAL ENVIRONMENT SETUP COMPLETE" -ForegroundColor Green
Write-Host "=" -NoNewline -ForegroundColor Green
Write-Host "="*79 -ForegroundColor Green
Write-Host ""

Write-Host "Created .env file with your credentials" -ForegroundColor Cyan
Write-Host ""

Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Install dependencies:" -ForegroundColor White
Write-Host "     python -m venv venv" -ForegroundColor Gray
Write-Host "     venv\Scripts\activate" -ForegroundColor Gray
Write-Host "     pip install -r requirements.txt" -ForegroundColor Gray
Write-Host ""
Write-Host "  2. Test API connections:" -ForegroundColor White
Write-Host "     python scripts/export_samples.py" -ForegroundColor Gray
Write-Host ""
Write-Host "  3. Run data audit:" -ForegroundColor White
Write-Host "     python scripts/data_audit.py" -ForegroundColor Gray
Write-Host ""

Write-Host "⚠️  Security reminders:" -ForegroundColor Yellow
Write-Host "  • .env file is gitignored - never commit it" -ForegroundColor White
Write-Host "  • Rotate API keys every 90 days" -ForegroundColor White
Write-Host "  • For production, use AWS Secrets Manager instead" -ForegroundColor White
Write-Host ""
