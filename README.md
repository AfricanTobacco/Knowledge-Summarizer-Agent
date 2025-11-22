# Knowledge Summarizer Agent

AI-powered knowledge management system that ingests, processes, and surfaces insights from Slack, Notion, and Google Drive with POPIA compliance.

## Project Overview

**Mission**: Automatically summarize and retrieve organizational knowledge from multiple sources while maintaining data privacy and compliance with POPIA regulations.

**Architecture**: GCP Dataflow → AWS Lambda → Pinecone Vector DB → Slack Bot

## Phase 1: Discovery + Data Audit + Compliance Mapping

### Deliverables

1. **API Access Configuration**
   - Slack OAuth tokens and Bot integration
   - Notion integration with service account
   - Google Drive API access with service credentials

2. **Sample Data Export**
   - 500 Slack messages (anonymized)
   - 20 Notion pages
   - 10 Google Drive documents

3. **Data Audit Report**
   - PII detection (emails, API keys, personal data)
   - Volume estimates (tokens per week)
   - Cost projections for embedding generation

4. **Compliance Checklist**
   - POPIA storage requirements
   - Data retention policy
   - Privacy impact assessment

5. **Architecture Diagram**
   - Data flow from sources to vector DB
   - Lambda processing pipeline
   - Slack bot response system

### Team Ownership

- **Team Jerome**: Infrastructure setup (GCP, Lambda, Pinecone)
- **Team Mako**: Compliance review and POPIA alignment

### Success Metrics

- ✅ API credentials working (test queries return data)
- ✅ No PII leaks in sample embeddings (manual review)
- ✅ Cost estimate for 1M tokens/month: <$50

### Go/No-Go Criteria

If API rate limits block real-time ingestion, pivot to batch-only mode:
- Switch from 15-minute refresh to 6-hour batch processing
- Implement queue-based processing for high-volume periods

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Configure API credentials
cp .env.example .env
# Edit .env with your credentials

# Run data audit
python scripts/data_audit.py

# Export sample data
python scripts/export_samples.py

# Run PII scan
python scripts/pii_scanner.py
```

## Project Structure

```
knowledge-summarizer-agent/
├── api/                    # API integration modules
│   ├── slack_client.py
│   ├── notion_client.py
│   └── drive_client.py
├── audit/                  # Data audit and compliance
│   ├── pii_scanner.py
│   ├── volume_estimator.py
│   └── compliance_checker.py
├── ingestion/              # Data ingestion pipeline
│   ├── dataflow/          # GCP Dataflow jobs
│   └── lambda/            # AWS Lambda functions
├── vector_db/              # Pinecone integration
│   └── embeddings.py
├── bot/                    # Slack bot
│   └── slack_bot.py
├── scripts/                # Utility scripts
│   ├── data_audit.py
│   ├── export_samples.py
│   └── cost_estimator.py
├── docs/                   # Documentation
│   ├── COMPLIANCE.md
│   ├── ARCHITECTURE.md
│   └── API_SETUP.md
└── tests/                  # Test suite
```

## Environment Variables

See [.env.example](.env.example) for required configuration.

## Documentation

- [API Setup Guide](docs/API_SETUP.md) - Configure Slack, Notion, Drive APIs
- [Compliance Checklist](docs/COMPLIANCE.md) - POPIA requirements
- [Architecture Overview](docs/ARCHITECTURE.md) - System design and data flow
- [Cost Estimation](docs/COST_ESTIMATION.md) - Budget planning

## License

Proprietary - African Tobacco
