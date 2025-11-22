# Setup AWS Secrets Manager for Knowledge Summarizer Agent
# This script creates secrets in AWS Secrets Manager for the application

param(
    [string]$Region = "us-west-2"
)

Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host "="*79 -ForegroundColor Cyan
Write-Host "Knowledge Summarizer Agent - AWS Secrets Setup" -ForegroundColor Cyan
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

# Function to create or update secret
function Set-AWSSecret {
    param(
        [string]$SecretName,
        [string]$SecretValue,
        [string]$Description
    )

    Write-Host "📝 Setting secret: $SecretName" -ForegroundColor Yellow

    # Check if secret exists
    try {
        aws secretsmanager describe-secret --secret-id $SecretName --region $Region 2>$null | Out-Null
        $exists = $true
    } catch {
        $exists = $false
    }

    if ($exists) {
        # Update existing secret
        aws secretsmanager put-secret-value `
            --secret-id $SecretName `
            --secret-string $SecretValue `
            --region $Region | Out-Null
        Write-Host "   ✅ Updated existing secret" -ForegroundColor Green
    } else {
        # Create new secret
        aws secretsmanager create-secret `
            --name $SecretName `
            --description $Description `
            --secret-string $SecretValue `
            --region $Region | Out-Null
        Write-Host "   ✅ Created new secret" -ForegroundColor Green
    }
}

# 1. Slack credentials
Write-Host ""
Write-Host "1️⃣  SLACK CREDENTIALS" -ForegroundColor Cyan
Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host "="*79 -ForegroundColor Cyan

$slackBotToken = Read-Host "Enter Slack Bot Token (xoxb-...)"
$slackAppToken = Read-Host "Enter Slack App Token (xapp-...)"
$slackSigningSecret = Read-Host "Enter Slack Signing Secret"

$slackSecret = @{
    slack_bot_token = $slackBotToken
    slack_app_token = $slackAppToken
    slack_signing_secret = $slackSigningSecret
} | ConvertTo-Json -Compress

Set-AWSSecret `
    -SecretName "knowledge-summarizer-slack" `
    -SecretValue $slackSecret `
    -Description "Slack API credentials for Knowledge Summarizer Agent"

# 2. Notion credentials
Write-Host ""
Write-Host "2️⃣  NOTION CREDENTIALS" -ForegroundColor Cyan
Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host "="*79 -ForegroundColor Cyan

$notionApiKey = Read-Host "Enter Notion API Key (secret_...)"
$notionDatabaseId = Read-Host "Enter Notion Database ID (optional, press Enter to skip)"

$notionSecret = @{
    notion_api_key = $notionApiKey
    notion_database_id = $notionDatabaseId
} | ConvertTo-Json -Compress

Set-AWSSecret `
    -SecretName "knowledge-summarizer-notion" `
    -SecretValue $notionSecret `
    -Description "Notion API credentials for Knowledge Summarizer Agent"

# 3. Google Drive credentials
Write-Host ""
Write-Host "3️⃣  GOOGLE DRIVE CREDENTIALS" -ForegroundColor Cyan
Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host "="*79 -ForegroundColor Cyan

$gcpKeyPath = Read-Host "Enter path to GCP service account JSON file"

if (Test-Path $gcpKeyPath) {
    $gcpKeyContent = Get-Content $gcpKeyPath -Raw

    Set-AWSSecret `
        -SecretName "knowledge-summarizer-gcp-service-account" `
        -SecretValue $gcpKeyContent `
        -Description "GCP service account for Google Drive access"

    Write-Host "✅ GCP service account key uploaded" -ForegroundColor Green
} else {
    Write-Host "⚠️  File not found: $gcpKeyPath - skipping" -ForegroundColor Yellow
}

# 4. Pinecone credentials
Write-Host ""
Write-Host "4️⃣  PINECONE CREDENTIALS" -ForegroundColor Cyan
Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host "="*79 -ForegroundColor Cyan

$pineconeApiKey = Read-Host "Enter Pinecone API Key"
$pineconeEnvironment = Read-Host "Enter Pinecone Environment (e.g., us-west1-gcp)"
$pineconeIndexName = Read-Host "Enter Pinecone Index Name (default: knowledge-summarizer)"

if ([string]::IsNullOrEmpty($pineconeIndexName)) {
    $pineconeIndexName = "knowledge-summarizer"
}

$pineconeSecret = @{
    pinecone_api_key = $pineconeApiKey
    pinecone_environment = $pineconeEnvironment
    pinecone_index_name = $pineconeIndexName
} | ConvertTo-Json -Compress

Set-AWSSecret `
    -SecretName "knowledge-summarizer-pinecone" `
    -SecretValue $pineconeSecret `
    -Description "Pinecone vector database credentials"

# 5. OpenAI credentials
Write-Host ""
Write-Host "5️⃣  OPENAI CREDENTIALS" -ForegroundColor Cyan
Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host "="*79 -ForegroundColor Cyan

$openaiApiKey = Read-Host "Enter OpenAI API Key (sk-...)"

$openaiSecret = @{
    openai_api_key = $openaiApiKey
} | ConvertTo-Json -Compress

Set-AWSSecret `
    -SecretName "knowledge-summarizer-openai" `
    -SecretValue $openaiSecret `
    -Description "OpenAI API credentials for embeddings"

# 6. Anthropic credentials
Write-Host ""
Write-Host "6️⃣  ANTHROPIC CREDENTIALS" -ForegroundColor Cyan
Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host "="*79 -ForegroundColor Cyan

$anthropicApiKey = Read-Host "Enter Anthropic API Key (sk-ant-...)"

$anthropicSecret = @{
    anthropic_api_key = $anthropicApiKey
} | ConvertTo-Json -Compress

Set-AWSSecret `
    -SecretName "knowledge-summarizer-anthropic" `
    -SecretValue $anthropicSecret `
    -Description "Anthropic API credentials for summarization"

# Summary
Write-Host ""
Write-Host "=" -NoNewline -ForegroundColor Green
Write-Host "="*79 -ForegroundColor Green
Write-Host "✅ SECRETS SETUP COMPLETE" -ForegroundColor Green
Write-Host "=" -NoNewline -ForegroundColor Green
Write-Host "="*79 -ForegroundColor Green
Write-Host ""

Write-Host "Created/Updated secrets in region: $Region" -ForegroundColor Cyan
Write-Host ""
Write-Host "Secrets created:" -ForegroundColor Yellow
Write-Host "  ✅ knowledge-summarizer-slack" -ForegroundColor Green
Write-Host "  ✅ knowledge-summarizer-notion" -ForegroundColor Green
Write-Host "  ✅ knowledge-summarizer-gcp-service-account" -ForegroundColor Green
Write-Host "  ✅ knowledge-summarizer-pinecone" -ForegroundColor Green
Write-Host "  ✅ knowledge-summarizer-openai" -ForegroundColor Green
Write-Host "  ✅ knowledge-summarizer-anthropic" -ForegroundColor Green
Write-Host ""

Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Verify secrets: aws secretsmanager list-secrets --region $Region" -ForegroundColor White
Write-Host "  2. Test retrieval: aws secretsmanager get-secret-value --secret-id knowledge-summarizer-slack --region $Region" -ForegroundColor White
Write-Host "  3. Update Lambda/Terraform to use these secrets" -ForegroundColor White
Write-Host ""
