# GCP Deployment Guide

This guide walks you through deploying the Knowledge Summarizer Agent to Google Cloud Platform.

## Prerequisites

- [x] GCP account with billing enabled
- [x] `gcloud` CLI installed and configured
- [x] All API credentials obtained (Slack, Notion, Drive, OpenAI, Anthropic, Pinecone)
- [x] `.env` file configured with credentials

## Step 1: Set Up GCP Project

```bash
# Create a new GCP project (or use existing)
export GCP_PROJECT_ID="knowledge-summarizer-prod"
export GCP_REGION="us-central1"

# Set as default project
gcloud config set project $GCP_PROJECT_ID
```

## Step 2: Enable Required APIs

The deployment script will automatically enable these, but you can do it manually:

```bash
gcloud services enable cloudfunctions.googleapis.com
gcloud services enable cloudscheduler.googleapis.com
gcloud services enable pubsub.googleapis.com
gcloud services enable logging.googleapis.com
gcloud services enable secretmanager.googleapis.com
```

## Step 3: Store Secrets

It's recommended to use Secret Manager for API keys:

```bash
# Store secrets
echo -n "your-slack-bot-token" | gcloud secrets create slack-bot-token --data-file=-
echo -n "your-notion-api-key" | gcloud secrets create notion-api-key --data-file=-
echo -n "your-openai-api-key" | gcloud secrets create openai-api-key --data-file=-
echo -n "your-anthropic-api-key" | gcloud secrets create anthropic-api-key --data-file=-
echo -n "your-pinecone-api-key" | gcloud secrets create pinecone-api-key --data-file=-

# Grant Cloud Functions access to secrets
PROJECT_NUMBER=$(gcloud projects describe $GCP_PROJECT_ID --format='value(projectNumber)')
gcloud secrets add-iam-policy-binding slack-bot-token \
    --member="serviceAccount:$PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
# Repeat for other secrets...
```

## Step 4: Deploy Cloud Functions

### Option A: Using Deployment Script (Recommended)

**On Linux/Mac:**
```bash
chmod +x infrastructure/deploy.sh
export GCP_PROJECT_ID="your-project-id"
./infrastructure/deploy.sh
```

**On Windows (PowerShell):**
```powershell
$env:GCP_PROJECT_ID="your-project-id"
.\infrastructure\deploy.ps1
```

### Option B: Manual Deployment

```bash
# Deploy ingest function
gcloud functions deploy ingest_function \
    --gen2 \
    --runtime python311 \
    --region $GCP_REGION \
    --trigger-topic knowledge-ingestion \
    --entry-point ingest_function \
    --source infrastructure/cloud_functions \
    --set-env-vars PROJECT_ID=$GCP_PROJECT_ID \
    --memory 512MB \
    --timeout 540s

# Deploy query function
gcloud functions deploy query_function \
    --gen2 \
    --runtime python311 \
    --region $GCP_REGION \
    --trigger-http \
    --allow-unauthenticated \
    --entry-point query_function \
    --source infrastructure/cloud_functions \
    --memory 512MB \
    --timeout 30s

# Deploy digest function
gcloud functions deploy digest_function \
    --gen2 \
    --runtime python311 \
    --region $GCP_REGION \
    --trigger-http \
    --entry-point generate_weekly_digest \
    --source infrastructure/cloud_functions \
    --memory 256MB \
    --timeout 120s
```

## Step 5: Configure Environment Variables

Set environment variables for each function:

```bash
gcloud functions deploy ingest_function \
    --update-env-vars \
    OPENAI_API_KEY=projects/$GCP_PROJECT_ID/secrets/openai-api-key/versions/latest,\
    PINECONE_API_KEY=projects/$GCP_PROJECT_ID/secrets/pinecone-api-key/versions/latest,\
    PINECONE_ENVIRONMENT=gcp-starter,\
    PINECONE_INDEX_NAME=knowledge-summarizer,\
    MONTHLY_BUDGET_USD=100
```

## Step 6: Set Up Pub/Sub Triggers

The Pub/Sub topics are created by the deployment script. Now configure your data sources to publish to these topics:

### Slack Events
```bash
# Add Slack webhook URL in Slack app settings:
# https://pubsub.googleapis.com/v1/projects/$GCP_PROJECT_ID/topics/slack-events:publish
```

### Notion Webhooks
```bash
# Configure Notion integration to post to:
# https://pubsub.googleapis.com/v1/projects/$GCP_PROJECT_ID/topics/notion-events:publish
```

### Google Drive
Use Drive API with service account to monitor changes and publish events.

## Step 7: Set Up Cloud Scheduler

The weekly digest scheduler is created automatically. Verify it:

```bash
gcloud scheduler jobs list --location=$GCP_REGION
```

To test the digest manually:
```bash
gcloud scheduler jobs run weekly-knowledge-digest --location=$GCP_REGION
```

## Step 8: Deploy and Configure Slack Bot

The Slack bot runs separately from Cloud Functions (on a VM or Cloud Run):

### Option A: Cloud Run (Recommended)

```bash
# Build container
gcloud builds submit --tag gcr.io/$GCP_PROJECT_ID/knowledge-bot bot/

# Deploy to Cloud Run
gcloud run deploy knowledge-bot \
    --image gcr.io/$GCP_PROJECT_ID/knowledge-bot \
    --platform managed \
    --region $GCP_REGION \
    --allow-unauthenticated \
    --set-env-vars \
        SLACK_BOT_TOKEN=projects/$GCP_PROJECT_ID/secrets/slack-bot-token/versions/latest,\
        SLACK_APP_TOKEN=projects/$GCP_PROJECT_ID/secrets/slack-app-token/versions/latest,\
        ANTHROPIC_API_KEY=projects/$GCP_PROJECT_ID/secrets/anthropic-api-key/versions/latest
```

### Option B: Compute Engine VM

```bash
# Create VM
gcloud compute instances create knowledge-bot \
    --machine-type=e2-micro \
    --zone=us-central1-a

# SSH and set up
gcloud compute ssh knowledge-bot --zone=us-central1-a

# On the VM:
git clone https://github.com/AfricanTobacco/Knowledge-Summarizer-Agent.git
cd Knowledge-Summarizer-Agent
pip install -r requirements.txt
# Copy .env file
nohup python bot/slack_bot.py &
```

## Step 9: Verify Deployment

### Test Cloud Functions

```bash
# Test query function
QUERY_URL=$(gcloud functions describe query_function --region $GCP_REGION --gen2 --format='value(serviceConfig.uri)')

curl -X POST $QUERY_URL \
    -H "Content-Type: application/json" \
    -d '{"query": "test query", "top_k": 5}'
```

### Test Slack Bot

In Slack, try:
```
/summarize how do I set up a new project?
```

### Check Logs

```bash
# View function logs
gcloud functions logs read ingest_function --region=$GCP_REGION --limit=50

# View all logs
gcloud logging read "resource.type=cloud_function" --limit=50 --format=json
```

## Step 10: Monitor Costs

Set up budget alerts:

```bash
# Create budget
gcloud billing budgets create \
    --billing-account=YOUR_BILLING_ACCOUNT_ID \
    --display-name="Knowledge Summarizer Budget" \
    --budget-amount=100USD
```

Monitor costs in GCP Console:
- **Cloud Functions**: Check invocations and compute time
- **Pinecone**: Monitor via Pinecone dashboard
- **OpenAI**: Track via OpenAI dashboard

## Troubleshooting

### Function Deployment Fails

```bash
# Check deployment logs
gcloud functions logs read function-name --region=$GCP_REGION --limit=100

# Validate source code
gcloud functions deploy function-name --dry-run
```

### Pub/Sub Messages Not Triggering Functions

```bash
# Check Pub/Sub subscriptions
gcloud pubsub subscriptions list

# Verify topic exists
gcloud pubsub topics list
```

### High Costs

1. Check OpenAI usage in embedder cost summary
2. Review Cloud Functions invocation counts
3. Verify budget alerts are configured
4. Consider switching to smaller embedding model or reducing chunk size

## Production Checklist

- [ ] All API credentials stored in Secret Manager
- [ ] Budget alerts configured
- [ ] Cloud Functions have appropriate timeout and memory limits
- [ ] Logging and monitoring set up
- [ ] PII redaction tested and verified
- [ ] Slack bot running continuously (Cloud Run or managed VM)
- [ ] Weekly digest scheduled and tested
- [ ] Backup strategy for Pinecone index
- [ ] Incident response plan documented

## Teardown

To remove all resources:

```bash
# Delete Cloud Functions
gcloud functions delete ingest_function --region=$GCP_REGION --quiet
gcloud functions delete query_function --region=$GCP_REGION --quiet
gcloud functions delete embed_function --region=$GCP_REGION --quiet
gcloud functions delete digest_function --region=$GCP_REGION --quiet

# Delete Pub/Sub topics
gcloud pubsub topics delete knowledge-ingestion --quiet
gcloud pubsub topics delete slack-events --quiet
gcloud pubsub topics delete notion-events --quiet
gcloud pubsub topics delete drive-events --quiet

# Delete Cloud Scheduler job
gcloud scheduler jobs delete weekly-knowledge-digest --location=$GCP_REGION --quiet

# Delete secrets
gcloud secrets delete slack-bot-token --quiet
gcloud secrets delete openai-api-key --quiet
gcloud secrets delete pinecone-api-key --quiet
```

## Support

For issues, contact:
- **Team Jerome**: Infrastructure and deployment
- **Team Mako**: Compliance and testing
