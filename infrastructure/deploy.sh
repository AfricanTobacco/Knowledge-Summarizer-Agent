#!/bin/bash

# GCP Deployment Script for Knowledge Summarizer Agent
# This script deploys all Cloud Functions and sets up infrastructure

set -e  # Exit on error

# Color codes for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Knowledge Summarizer Agent - GCP Deployment${NC}"
echo -e "${BLUE}========================================${NC}"

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}Error: gcloud CLI not found. Please install it first.${NC}"
    exit 1
fi

# Configuration
PROJECT_ID=${GCP_PROJECT_ID:-""}
REGION=${GCP_REGION:-"us-central1"}

if [ -z "$PROJECT_ID" ]; then
    echo -e "${RED}Error: GCP_PROJECT_ID environment variable not set${NC}"
    echo "Please run: export GCP_PROJECT_ID=your-project-id"
    exit 1
fi

echo -e "${GREEN}Using GCP Project: $PROJECT_ID${NC}"
echo -e "${GREEN}Region: $REGION${NC}"

# Set project
gcloud config set project $PROJECT_ID

# Enable required APIs
echo -e "\n${BLUE}Enabling required GCP APIs...${NC}"
gcloud services enable cloudfunctions.googleapis.com
gcloud services enable cloudscheduler.googleapis.com
gcloud services enable pubsub.googleapis.com
gcloud services enable cloudlogger.googleapis.com

# Create Pub/Sub topics
echo -e "\n${BLUE}Creating Pub/Sub topics...${NC}"
gcloud pubsub topics create knowledge-ingestion --quiet || echo "Topic already exists"
gcloud pubsub topics create slack-events --quiet || echo "Topic already exists"
gcloud pubsub topics create notion-events --quiet || echo "Topic already exists"
gcloud pubsub topics create drive-events --quiet || echo "Topic already exists"

# Deploy Cloud Functions
echo -e "\n${BLUE}Deploying Cloud Functions...${NC}"

# 1. Ingest Function (Pub/Sub triggered)
echo -e "${GREEN}Deploying ingest_function...${NC}"
gcloud functions deploy ingest_function \
    --gen2 \
    --runtime python311 \
    --region $REGION \
    --trigger-topic knowledge-ingestion \
    --entry-point ingest_function \
    --source infrastructure/cloud_functions \
    --set-env-vars PROJECT_ID=$PROJECT_ID \
    --memory 512MB \
    --timeout 540s \
    --quiet

# 2. Embed Function (HTTP triggered)
echo -e "${GREEN}Deploying embed_function...${NC}"
gcloud functions deploy embed_function \
    --gen2 \
    --runtime python311 \
    --region $REGION \
    --trigger-http \
    --allow-unauthenticated \
    --entry-point embed_function \
    --source infrastructure/cloud_functions \
    --memory 256MB \
    --timeout 60s \
    --quiet

# 3. Query Function (HTTP triggered)
echo -e "${GREEN}Deploying query_function...${NC}"
gcloud functions deploy query_function \
    --gen2 \
    --runtime python311 \
    --region $REGION \
    --trigger-http \
    --allow-unauthenticated \
    --entry-point query_function \
    --source infrastructure/cloud_functions \
    --memory 512MB \
    --timeout 30s \
    --quiet

# 4. Weekly Digest Function (HTTP triggered, for Cloud Scheduler)
echo -e "${GREEN}Deploying digest_function...${NC}"
gcloud functions deploy digest_function \
    --gen2 \
    --runtime python311 \
    --region $REGION \
    --trigger-http \
    --entry-point generate_weekly_digest \
    --source infrastructure/cloud_functions \
    --memory 256MB \
    --timeout 120s \
    --quiet

# Get the digest function URL
DIGEST_URL=$(gcloud functions describe digest_function --region $REGION --gen2 --format='value(serviceConfig.uri)')

# Create Cloud Scheduler job for weekly digest
echo -e "\n${BLUE}Setting up Cloud Scheduler for weekly digest...${NC}"
gcloud scheduler jobs create http weekly-knowledge-digest \
    --location $REGION \
    --schedule "0 9 * * 1" \
    --uri "$DIGEST_URL" \
    --http-method POST \
    --time-zone "America/New_York" \
    --quiet || echo "Scheduler job already exists"

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"

echo -e "\nDeployed Functions:"
echo -e "  • ingest_function (Pub/Sub trigger)"
echo -e "  • embed_function (HTTP)"
echo -e "  • query_function (HTTP)"
echo -e "  • digest_function (HTTP)"

echo -e "\nScheduled Jobs:"
echo -e "  • weekly-knowledge-digest (Mondays at 9 AM)"

echo -e "\n${BLUE}Next Steps:${NC}"
echo -e "1. Set up environment variables in Cloud Functions console"
echo -e "2. Configure Slack webhooks to publish to 'slack-events' topic"
echo -e "3. Configure Notion webhooks to publish to 'notion-events' topic"
echo -e "4. Set up Drive API to publish to 'drive-events' topic"
echo -e "5. Test the Slack bot with /summarize command"

echo -e "\n${GREEN}Deployment script completed successfully!${NC}"
