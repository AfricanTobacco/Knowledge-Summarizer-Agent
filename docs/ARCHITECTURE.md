# Knowledge Summarizer Agent - Architecture

## System Overview

The Knowledge Summarizer Agent is a distributed AI system that ingests organizational knowledge from multiple sources, generates semantic embeddings, and provides intelligent retrieval via a Slack bot.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         DATA SOURCES                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐        │
│  │    Slack     │   │    Notion    │   │ Google Drive │        │
│  │  Workspace   │   │  Workspace   │   │   Folders    │        │
│  └──────┬───────┘   └──────┬───────┘   └──────┬───────┘        │
│         │                  │                   │                 │
│         └──────────────────┼───────────────────┘                 │
│                            │                                     │
└────────────────────────────┼─────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    INGESTION PIPELINE                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              GCP Cloud Dataflow                          │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐        │   │
│  │  │  Extract   │→ │ Transform  │→ │   Load     │        │   │
│  │  │   (API)    │  │ (Clean/PII)│  │  (Queue)   │        │   │
│  │  └────────────┘  └────────────┘  └────────────┘        │   │
│  │                                                          │   │
│  │  Features:                                               │   │
│  │  • 15-min streaming OR 6-hour batch                     │   │
│  │  • PII detection and anonymization                      │   │
│  │  • Deduplication and change detection                   │   │
│  │  • Rate limiting and backpressure handling              │   │
│  └─────────────────────────────────────────────────────────┘   │
│                            │                                     │
│                            ▼                                     │
│                   ┌─────────────────┐                           │
│                   │  GCP Pub/Sub    │                           │
│                   │  Message Queue  │                           │
│                   └────────┬────────┘                           │
└─────────────────────────────┼───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PROCESSING LAYER                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │           AWS Lambda Functions                           │   │
│  │                                                          │   │
│  │  ┌──────────────────┐  ┌──────────────────┐            │   │
│  │  │ Embedding Lambda │  │Summary Lambda    │            │   │
│  │  │                  │  │                  │            │   │
│  │  │ • OpenAI API     │  │ • Claude API     │            │   │
│  │  │ • Batch 100 docs │  │ • Summarization  │            │   │
│  │  │ • 1536-dim vector│  │ • Insight extract│            │   │
│  │  └────────┬─────────┘  └────────┬─────────┘            │   │
│  │           │                     │                       │   │
│  │           ▼                     ▼                       │   │
│  │  ┌──────────────────────────────────────┐              │   │
│  │  │       DLQ (Dead Letter Queue)        │              │   │
│  │  │  • Failed embeddings                 │              │   │
│  │  │  • Retry with exponential backoff    │              │   │
│  │  └──────────────────────────────────────┘              │   │
│  └─────────────────────────────────────────────────────────┘   │
│                            │                                     │
└────────────────────────────┼─────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                     VECTOR DATABASE                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              Pinecone Vector DB                          │   │
│  │                                                          │   │
│  │  Index: knowledge-summarizer                            │   │
│  │  Dimensions: 1536 (OpenAI ada-002)                      │   │
│  │  Metric: Cosine similarity                              │   │
│  │  Namespace: {slack, notion, drive}                      │   │
│  │                                                          │   │
│  │  Metadata:                                               │   │
│  │  • source_type (slack/notion/drive)                     │   │
│  │  • source_id (message_id/page_id/file_id)               │   │
│  │  • timestamp                                             │   │
│  │  • author (anonymized if required)                      │   │
│  │  • channel/workspace                                     │   │
│  │  • summary (Claude-generated)                           │   │
│  └─────────────────────────────────────────────────────────┘   │
│                            │                                     │
└────────────────────────────┼─────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                       QUERY LAYER                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              Slack Bot (AWS Lambda)                      │   │
│  │                                                          │   │
│  │  Commands:                                               │   │
│  │  • /summarize [topic]   → Get summary of topic          │   │
│  │  │  • /search [query]      → Semantic search            │   │
│  │  • /digest [timeframe]  → Time-based digest             │   │
│  │  • /insights            → AI-generated insights         │   │
│  │  • /help                → Usage guide                   │   │
│  │  • /privacy             → POPIA notice                  │   │
│  │                                                          │   │
│  │  Flow:                                                   │   │
│  │  1. Receive Slack command                               │   │
│  │  2. Generate query embedding (OpenAI)                   │   │
│  │  3. Query Pinecone (top 10 results)                     │   │
│  │  4. Re-rank with Claude                                 │   │
│  │  5. Generate response summary                           │   │
│  │  6. Post to Slack with source links                     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                   MONITORING & COMPLIANCE                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ CloudWatch   │  │  Stackdriver │  │    Sentry    │         │
│  │   Metrics    │  │     Logs     │  │ Error Track  │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                 Compliance Monitoring                    │   │
│  │  • PII leak detection (weekly scans)                    │   │
│  │  • Data retention enforcement (24h delete SLA)          │   │
│  │  • Access audit logs (12-month retention)               │   │
│  │  • Cost tracking (budget alerts at 80%)                 │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. Data Sources

**Slack Workspace**
- **API**: Slack Web API (conversations.history, search.messages)
- **Auth**: OAuth 2.0 Bot Token
- **Rate Limits**: 50+ requests/minute (Tier 2)
- **Data**: Messages, threads, reactions, files

**Notion Workspace**
- **API**: Notion API v1
- **Auth**: Integration Token
- **Rate Limits**: 3 requests/second
- **Data**: Pages, databases, blocks

**Google Drive**
- **API**: Google Drive API v3
- **Auth**: Service Account
- **Rate Limits**: 1000 queries/100 seconds/user
- **Data**: Docs, Sheets, PDFs

### 2. Ingestion Pipeline (GCP Dataflow)

**Extract Stage**
- Poll APIs every 15 minutes (streaming) or 6 hours (batch)
- Fetch new/updated content since last sync
- Handle pagination and rate limits

**Transform Stage**
- **PII Detection**: Scan for emails, phone numbers, API keys, IDs
- **Anonymization**: Redact detected PII
- **Normalization**: Convert to standard schema
- **Deduplication**: Skip unchanged content (hash comparison)

**Load Stage**
- Publish to GCP Pub/Sub queue
- Include metadata (source, timestamp, author)
- Handle backpressure with queue buffering

**Go/No-Go Pivot**
- If rate limits block real-time ingestion → Switch to 6-hour batch
- Criteria: >10% failed API calls in 1-hour window

### 3. Processing Layer (AWS Lambda)

**Embedding Lambda**
- **Trigger**: Pub/Sub messages (batch up to 100)
- **API**: OpenAI Embeddings API (ada-002)
- **Output**: 1536-dimension vectors
- **Timeout**: 5 minutes
- **Memory**: 2GB
- **Retries**: 3 attempts with exponential backoff

**Summary Lambda**
- **Trigger**: Pub/Sub messages (batch up to 20)
- **API**: Claude Sonnet API
- **Prompt**: "Summarize in 1-2 sentences for search retrieval"
- **Output**: Summary text + key topics
- **Timeout**: 3 minutes
- **Memory**: 1GB

**Dead Letter Queue (DLQ)**
- Capture failed embeddings/summaries
- Retry after 5 minutes, then 15 minutes, then manual review
- Alert Team Jerome on DLQ depth > 100

### 4. Vector Database (Pinecone)

**Index Configuration**
- **Name**: knowledge-summarizer
- **Dimensions**: 1536
- **Metric**: Cosine similarity
- **Replicas**: 1 (pilot), 2 (production)
- **Pods**: 1x p1.x1 (pilot), 2x p1.x2 (production)

**Namespaces**
- `slack`: Slack messages
- `notion`: Notion pages
- `drive`: Google Drive documents

**Metadata Schema**
```json
{
  "source_type": "slack|notion|drive",
  "source_id": "unique_id",
  "timestamp": "2024-01-15T10:30:00Z",
  "author": "user@example.com",  // Anonymized if POPIA requires
  "channel": "general",
  "summary": "Claude-generated summary",
  "url": "https://...",
  "tags": ["topic1", "topic2"]
}
```

### 5. Query Layer (Slack Bot)

**Slack Bot Lambda**
- **Trigger**: Slack Events API (slash commands)
- **Auth**: Slack Signing Secret verification
- **Flow**:
  1. Parse command and query text
  2. Generate query embedding (OpenAI)
  3. Search Pinecone (top_k=10)
  4. Re-rank with Claude (relevance scoring)
  5. Format response with source links
  6. Post to Slack channel

**Commands**
- `/summarize [topic]`: Get summary of all knowledge on topic
- `/search [query]`: Semantic search across all sources
- `/digest daily|weekly`: Time-based digest
- `/insights`: AI-generated insights from recent activity
- `/help`: Usage documentation
- `/privacy`: POPIA compliance notice

### 6. Monitoring & Compliance

**CloudWatch (AWS)**
- Lambda invocations, errors, duration
- DLQ depth alerts
- Cost tracking (billing alarms)

**Stackdriver (GCP)**
- Dataflow job status
- Pub/Sub queue depth
- API error rates

**Sentry**
- Application error tracking
- User-facing error alerting

**Compliance Monitoring**
- Weekly PII scans on sample data
- Data deletion SLA tracking (24-hour target)
- Access audit log retention (12 months)
- Cost alerts (80% of $50 budget)

## Data Flow Examples

### Example 1: Slack Message Ingestion

```
1. User posts message in #engineering channel
2. GCP Dataflow polls Slack API (15-min interval)
3. New message detected → Transform stage
4. PII scan: Detect and redact email address
5. Publish to Pub/Sub queue
6. Embedding Lambda triggered (batched with 99 other messages)
7. OpenAI generates 1536-dim vector
8. Summary Lambda generates 1-sentence summary
9. Upsert to Pinecone with metadata
10. Message now searchable via Slack bot
```

### Example 2: Slack Bot Query

```
1. User types: /search "How do we deploy to production?"
2. Slack sends event to Bot Lambda
3. Bot generates query embedding (OpenAI)
4. Pinecone search returns top 10 similar vectors
5. Claude re-ranks results by relevance
6. Bot formats response:
   "Found 3 relevant discussions:
   1. [Production deployment runbook](link) - @alice, Jan 15
   2. [CI/CD pipeline docs](link) - @bob, Jan 10
   3. [Deployment checklist](link) - @charlie, Dec 28"
7. Post formatted response to Slack
```

## Scalability

### Current Capacity (Pilot)
- **Slack Messages**: 1000/week
- **Notion Pages**: 100/week
- **Drive Docs**: 50/week
- **Total**: ~5000 new embeddings/week
- **Storage**: ~500MB vector data
- **Cost**: ~$25/month

### Production Capacity (Full Rollout)
- **Messages**: 10,000/week
- **Total**: ~50,000 new embeddings/week
- **Storage**: ~5GB vector data
- **Cost**: ~$200/month (needs budget increase)

### Scaling Strategies
1. **Horizontal**: Add more Lambda concurrency
2. **Batching**: Increase batch sizes (100 → 500)
3. **Caching**: Cache frequently accessed embeddings
4. **Sharding**: Partition Pinecone by team/project

## Security

### Encryption
- **In Transit**: TLS 1.3 for all API calls
- **At Rest**: Pinecone encryption, AWS EBS encryption, GCP encryption

### Access Control
- **AWS**: IAM roles with least privilege
- **GCP**: Service accounts with minimal scopes
- **Pinecone**: API key rotation every 90 days

### Secrets Management
- AWS Secrets Manager for API keys
- No hardcoded credentials

### Audit Logging
- All API calls logged (CloudWatch/Stackdriver)
- 12-month retention
- Anomaly detection alerts

## Disaster Recovery

### Backup Strategy
- **Pinecone**: Weekly vector database backup
- **Metadata**: Daily snapshot to S3
- **Audit Logs**: Replicated to GCS

### Recovery Objectives
- **RPO (Recovery Point Objective)**: 24 hours
- **RTO (Recovery Time Objective)**: 4 hours

### Failure Scenarios
- **Pinecone down**: Fallback to cached responses, alert Team Jerome
- **Lambda throttling**: Queue messages in Pub/Sub, process when capacity available
- **API rate limits**: Exponential backoff, switch to batch mode

## Cost Breakdown (Pilot)

| Component | Monthly Cost |
|-----------|-------------|
| OpenAI Embeddings | $10 |
| Claude Summarization | $5 |
| Pinecone Vector DB | $7 |
| AWS Lambda | $2 |
| GCP Dataflow | $3 |
| Total | $27 |

**Budget Compliance**: ✅ Within $50 target

## References
- [GCP Dataflow Documentation](https://cloud.google.com/dataflow/docs)
- [AWS Lambda Best Practices](https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html)
- [Pinecone Documentation](https://docs.pinecone.io/)
- [Slack API Documentation](https://api.slack.com/)
