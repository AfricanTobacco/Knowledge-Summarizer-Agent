# Quick Start Guide

Get the Knowledge Summarizer Agent up and running in 30 minutes.

## Prerequisites

- Python 3.9 or higher
- Git
- Admin access to Slack, Notion, and Google Drive

## Step 1: Clone Repository

```bash
cd /c/Users/_oloyouth
git clone https://github.com/AfricanTobacco/Knowledge-Summarizer-Agent.git
cd Knowledge-Summarizer-Agent
```

## Step 2: Install Dependencies

```bash
# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Mac/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Step 3: Configure API Credentials

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your credentials
# See docs/API_SETUP.md for detailed instructions
```

Required credentials:
- Slack Bot Token
- Notion API Key
- Google Drive Service Account
- OpenAI API Key
- Anthropic API Key
- Pinecone API Key

## Step 4: Create Credentials Directory

```bash
mkdir credentials
# Place google-service-account.json in credentials/
```

## Step 5: Export Sample Data

```bash
python scripts/export_samples.py
```

This will:
- ✅ Test API connections
- ✅ Export 500 Slack messages
- ✅ Export 20 Notion pages
- ✅ Export 10 Google Drive documents

Expected output:
```
✅ Exported 500 Slack messages
✅ Exported 20 Notion pages
✅ Exported 10 Drive documents
```

## Step 6: Run Data Audit

```bash
python scripts/data_audit.py
```

This will:
- 🔍 Scan for PII (emails, API keys, etc.)
- 📊 Estimate token volumes
- 💰 Calculate costs
- ✅ Generate go/no-go decision

Expected output:
```
PII Scan: ✅ PASSED
Budget Check: ✅ PASSED
DECISION: ✅ GO
```

## Step 7: Review Reports

Generated reports:
- `sample_slack_messages_pii_report.json` - PII scan results for Slack
- `sample_notion_pages_pii_report.json` - PII scan results for Notion
- `sample_drive_docs_pii_report.json` - PII scan results for Drive
- `volume_estimate_report.json` - Cost and volume projections
- `data_audit_report.json` - Combined go/no-go decision

## Step 8: Review Compliance

```bash
# Open compliance checklist
cat docs/COMPLIANCE.md
```

Ensure Team Mako reviews:
- POPIA requirements
- Data retention policy
- Privacy notice draft

## Step 9: (Optional) Deploy Infrastructure

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for:
- GCP Dataflow setup
- AWS Lambda deployment
- Pinecone index configuration
- Slack bot deployment

## Quick Commands

```bash
# Test Slack connection
python -c "from api.slack_client import SlackClient; SlackClient().test_connection()"

# Test Notion connection
python -c "from api.notion_client import NotionClient; NotionClient().test_connection()"

# Test Drive connection
python -c "from api.drive_client import DriveClient; DriveClient().test_connection()"

# Export samples
python scripts/export_samples.py

# Run audit
python scripts/data_audit.py

# Run PII scan only
python audit/pii_scanner.py

# Run volume estimation only
python audit/volume_estimator.py
```

## Success Metrics Checklist

Phase 1 deliverables:

- ✅ API credentials working (test queries return data)
- ✅ No PII leaks in sample embeddings (manual review)
- ✅ Cost estimate for 1M tokens/month: <$50

## Troubleshooting

### "Module not found" errors
```bash
# Ensure virtual environment is activated
venv\Scripts\activate  # Windows
source venv/bin/activate  # Mac/Linux

# Reinstall dependencies
pip install -r requirements.txt
```

### API connection failures
- Verify `.env` file exists and has correct credentials
- Check API setup guide: [docs/API_SETUP.md](docs/API_SETUP.md)
- Ensure service accounts are shared with workspaces

### Sample export returns empty data
- Verify workspaces have content
- Check API permissions (read access required)
- Ensure integrations are connected to pages/channels

## Next Steps

Once data audit passes:

1. **Team Jerome**: Set up infrastructure (GCP, AWS, Pinecone)
2. **Team Mako**: Complete compliance review
3. **Both Teams**: Deploy pilot to test workspace
4. **Monitor**: Track costs, PII leaks, and performance

## Support

- Documentation: See [docs/](docs/) folder
- Architecture: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- Compliance: [docs/COMPLIANCE.md](docs/COMPLIANCE.md)
- API Setup: [docs/API_SETUP.md](docs/API_SETUP.md)

## Go/No-Go Criteria

If API rate limits block real-time ingestion:
- **Pivot**: Switch from 15-minute refresh to 6-hour batch processing
- **Impact**: Longer data freshness window (acceptable for pilot)
- **Decision**: Proceed with batch-only mode

---

**Time to completion**: ~30 minutes (excluding API credential setup)

**Team ownership**:
- Infrastructure: Team Jerome
- Compliance: Team Mako
