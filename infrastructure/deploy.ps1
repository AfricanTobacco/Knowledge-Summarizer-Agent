# GCP Deployment Script for Knowledge Summarizer Agent (PowerShell)
# This script deploys all Cloud Functions and sets up infrastructure on Windows

param(
    [string]$ProjectId = $env:GCP_PROJECT_ID,
    [string]$Region = "us-central1"
)

Write-Host "========================================" -ForegroundColor Blue
Write-Host "Knowledge Summarizer Agent - GCP Deployment" -ForegroundColor Blue
Write-Host "========================================" -ForegroundColor Blue

# Check if gcloud is installed
if (!(Get-Command gcloud -ErrorAction SilentlyContinue)) {
    Write-Host "Error: gcloud CLI not found. Please install it first." -ForegroundColor Red
    exit 1
}

# Check project ID
if ([string]::IsNullOrEmpty($ProjectId)) {
    Write-Host "Error: GCP_PROJECT_ID not set" -ForegroundColor Red
    Write-Host "Please run: `$env:GCP_PROJECT_ID='your-project-id'" -ForegroundColor Yellow
    exit 1
}

Write-Host "Using GCP Project: $ProjectId" -ForegroundColor Green
Write-Host "Region: $Region" -ForegroundColor Green

# Set project
gcloud config set project $ProjectId

# Enable required APIs
Write-Host "`nEnabling required GCP APIs..." -ForegroundColor Blue
gcloud services enable cloudfunctions.googleapis.com
gcloud services enable cloudscheduler.googleapis.com
gcloud services enable pubsub.googleapis.com
gcloud services enable logging.googleapis.com

# Create Pub/Sub topics
Write-Host "`nCreating Pub/Sub topics..." -ForegroundColor Blue
$topics = @("knowledge-ingestion", "slack-events", "notion-events", "drive-events")
foreach ($topic in $topics) {
    try {
        gcloud pubsub topics create $topic --quiet
    } catch {
        Write-Host "Topic $topic already exists" -ForegroundColor Yellow
    }
}

# Deploy Cloud Functions
Write-Host "`nDeploying Cloud Functions..." -ForegroundColor Blue

# 1. Ingest Function
Write-Host "Deploying ingest_function..." -ForegroundColor Green
gcloud functions deploy ingest_function `
    --gen2 `
    --runtime python311 `
    --region $Region `
    --trigger-topic knowledge-ingestion `
    --entry-point ingest_function `
    --source infrastructure/cloud_functions `
    --set-env-vars PROJECT_ID=$ProjectId `
    --memory 512MB `
    --timeout 540s `
    --quiet

# 2. Embed Function
Write-Host "Deploying embed_function..." -ForegroundColor Green
gcloud functions deploy embed_function `
    --gen2 `
    --runtime python311 `
    --region $Region `
    --trigger-http `
    --allow-unauthenticated `
    --entry-point embed_function `
    --source infrastructure/cloud_functions `
    --memory 256MB `
    --timeout 60s `
    --quiet

# 3. Query Function
Write-Host "Deploying query_function..." -ForegroundColor Green
gcloud functions deploy query_function `
    --gen2 `
    --runtime python311 `
    --region $Region `
    --trigger-http `
    --allow-unauthenticated `
    --entry-point query_function `
    --source infrastructure/cloud_functions `
    --memory 512MB `
    --timeout 30s `
    --quiet

# 4. Digest Function
Write-Host "Deploying digest_function..." -ForegroundColor Green
gcloud functions deploy digest_function `
    --gen2 `
    --runtime python311 `
    --region $Region `
    --trigger-http `
    --entry-point generate_weekly_digest `
    --source infrastructure/cloud_functions `
    --memory 256MB `
    --timeout 120s `
    --quiet

# Get digest function URL
$digestUrl = gcloud functions describe digest_function --region $Region --gen2 --format='value(serviceConfig.uri)'

# Create Cloud Scheduler job
Write-Host "`nSetting up Cloud Scheduler for weekly digest..." -ForegroundColor Blue
try {
    gcloud scheduler jobs create http weekly-knowledge-digest `
        --location $Region `
        --schedule "0 9 * * 1" `
        --uri $digestUrl `
        --http-method POST `
        --time-zone "America/New_York" `
        --quiet
} catch {
    Write-Host "Scheduler job already exists" -ForegroundColor Yellow
}

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "Deployment Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green

Write-Host "`nDeployed Functions:"
Write-Host "  • ingest_function (Pub/Sub trigger)" -ForegroundColor Cyan
Write-Host "  • embed_function (HTTP)" -ForegroundColor Cyan
Write-Host "  • query_function (HTTP)" -ForegroundColor Cyan
Write-Host "  • digest_function (HTTP)" -ForegroundColor Cyan

Write-Host "`nScheduled Jobs:"
Write-Host "  • weekly-knowledge-digest (Mondays at 9 AM)" -ForegroundColor Cyan

Write-Host "`nNext Steps:" -ForegroundColor Blue
Write-Host "1. Set up environment variables in Cloud Functions console"
Write-Host "2. Configure Slack webhooks to publish to 'slack-events' topic"
Write-Host "3. Configure Notion webhooks to publish to 'notion-events' topic"
Write-Host "4. Set up Drive API to publish to 'drive-events' topic"
Write-Host "5. Test the Slack bot with /summarize command"

Write-Host "`nDeployment script completed successfully!" -ForegroundColor Green
