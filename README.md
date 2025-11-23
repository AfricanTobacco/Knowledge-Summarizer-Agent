# Knowledge Summarizer Agent

AI-powered knowledge management system that ingests, processes, and surfaces insights from Slack, Notion, and Google Drive with POPIA compliance.

## Project Overview

**Mission**: Automatically summarize and retrieve organizational knowledge from multiple sources while maintaining data privacy and compliance with POPIA regulations.

**Architecture**: GCP Cloud Functions + Cloud Pub/Sub + Pinecone Vector DB + Slack Bot

## Features

✅ **Multi-Source Ingestion**
- Slack message indexing with channel filtering
- Notion page monitoring with webhook support
- Google Drive document processing (PDF, DOCX, TXT)

✅ **Intelligent Processing**
- 500-token chunking with 50-token overlap
- PII redaction (emails, API keys, phone numbers)
- OpenAI embeddings with cost tracking
- Budget caps and alerts

✅ **Semantic Search**
- Pinecone vector database with namespace organization
- `/summarize` Slack command for instant answers
- Claude Haiku-powered summarization
- Weekly knowledge digests

✅ **Cost-Effective**
- **Prototype**: ~$20-55/month (leverages GCP free tiers)
- **At Scale**: ~$150-190/month
- Real-time cost monitoring and budget enforcement

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your API credentials
```

Required credentials:
- Slack OAuth token and App token
- Notion API key
- Google Drive service account
- Pinecone API key
- OpenAI API key
- Anthropic API key
- GCP project ID

### 3. Run Locally

```bash
# Test Slack bot
python bot/slack_bot.py

# Test processing pipeline
python processing/chunker.py
python processing/pii_redactor.py
python processing/embedder.py

# Test vector storage
python storage/pinecone_store.py
```

## Project Structure

```
knowledge-summarizer-agent/
├── api/                          # API integration modules
│   ├── slack_client.py           # Slack API client
│   ├── notion_client.py          # Notion API client
│   └── drive_client.py           # Google Drive client
├── processing/                   # Content processing
│   ├── chunker.py                # Text chunking (500 tokens)
│   ├── pii_redactor.py           # PII detection & redaction
│   └── embedder.py               # OpenAI embeddings + cost tracking
├── storage/                      # Vector DB and caching
│   ├── pinecone_store.py         # Pinecone vector operations
│   └── cache_manager.py          # Cloud Storage cache
├── bot/                          # Slack bot
│   └── slack_bot.py              # /summarize command handler
├── infrastructure/               # GCP deployment
│   └── cloud_functions/          # Cloud Functions
│       ├── main.py               # Ingestion, embed, query functions
│       ├── digest.py             # Weekly digest generator
│       └── requirements.txt      # Cloud Functions dependencies
├── audit/                        # Compliance & auditing
├── scripts/                      # Utility scripts
├── docs/                         # Documentation
└── tests/                        # Test suite
```

## Usage

### Slack Bot Commands

```
/summarize [your question]
```

Example:
```
/summarize how do I onboard a new client?
/summarize what are our security policies?
/summarize latest updates on Project Mako
```

The bot will:
1. Search the knowledge base semantically
2. Retrieve top 5 relevant chunks
3. Generate a summary with Claude
4. Return answer with source attribution

### Weekly Digest

Every week, the bot automatically posts a digest to #general with:
- Top 5 themes/updates from the past week
- Knowledge base statistics
- Reminder to use `/summarize` command

## Deployment to GCP

### Prerequisites

1. GCP project created
2. Cloud Functions API enabled
3. Cloud Pub/Sub API enabled
4. Cloud Scheduler API enabled
5. Service account with appropriate permissions

### Deploy Functions

```bash
# Deploy ingestion function (Pub/Sub trigger)
gcloud functions deploy ingest_function \
  --runtime python311 \
  --trigger-topic knowledge-ingestion \
  --entry-point ingest_function \
  --source infrastructure/cloud_functions \
  --set-env-vars PROJECT_ID=your-project-id

# Deploy query function (HTTP trigger)
gcloud functions deploy query_function \
  --runtime python311 \
  --trigger-http \
  --allow-unauthenticated \
  --entry-point query_function \
  --source infrastructure/cloud_functions

# Deploy weekly digest (Cloud Scheduler)
gcloud functions deploy digest_function \
  --runtime python311 \
  --trigger-http \
  --entry-point generate_weekly_digest \
  --source infrastructure/cloud_functions

# Create Cloud Scheduler job for weekly digest
gcloud scheduler jobs create http weekly-digest \
  --schedule="0 9 * * 1" \
  --uri=https://REGION-PROJECT_ID.cloudfunctions.net/digest_function \
  --http-method=POST
```

## Cost Management

The system includes built-in cost controls:

- **Budget Cap**: Default $100/month on OpenAI embeddings
- **Alert Threshold**: Warning at 75% budget usage
- **Auto-Halt**: Stops embedding generation if budget exceeded
- **Cost Tracking**: Real-time monitoring of token usage and costs

Update budget in `.env`:
```
MONTHLY_BUDGET_USD=100
ALERT_THRESHOLD_PERCENT=75
```

## Compliance (POPIA)

- PII redaction before embedding generation
- 90-day data retention policy
- Audit logging for all queries
- Access control (public channels only)
- Data anonymization in samples

## Documentation

- [QUICKSTART.md](QUICKSTART.md) - Getting started guide
- [API Setup Guide](docs/API_SETUP.md) - Configure Slack, Notion, Drive APIs
- [Compliance Checklist](docs/COMPLIANCE.md) - POPIA requirements
- [Architecture Overview](docs/ARCHITECTURE.md) - System design
- [Cost Estimation](docs/COST_ESTIMATION.md) - Budget planning

## Success Metrics

- ⏱️ 50-60% reduction in information retrieval time
- 🚀 3-4x faster onboarding for new hires
- 💰 Monthly cost: $20-55 (prototype), $150-190 (at scale)
- 🔍 Query response time: <3 seconds
- 📊 Knowledge base coverage: 90%+ of Slack, Notion, Drive content

## Team Ownership

- **Team Jerome**: Infrastructure, GCP deployment, monitoring
- **Team Mako**: Compliance, POPIA alignment, testing

## License

Proprietary - African Tobacco
