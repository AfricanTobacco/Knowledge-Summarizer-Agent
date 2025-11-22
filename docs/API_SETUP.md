# API Setup Guide

This guide walks you through setting up API access for Slack, Notion, and Google Drive.

## Prerequisites

- Admin access to your Slack workspace
- Admin access to your Notion workspace
- Google Workspace admin access (for Drive)

---

## 1. Slack API Setup

### Create Slack App

1. Go to [Slack API Console](https://api.slack.com/apps)
2. Click **Create New App** → **From scratch**
3. Enter app name: "Knowledge Summarizer Agent"
4. Select your workspace
5. Click **Create App**

### Configure Bot Permissions

1. Navigate to **OAuth & Permissions**
2. Scroll to **Scopes** → **Bot Token Scopes**
3. Add the following scopes:
   - `channels:history` - View messages in public channels
   - `channels:read` - View basic channel info
   - `chat:write` - Send messages as the bot
   - `groups:history` - View messages in private channels
   - `groups:read` - View basic private channel info
   - `users:read` - View people in workspace
   - `search:read` - Search workspace content

### Install App to Workspace

1. Scroll to **OAuth Tokens for Your Workspace**
2. Click **Install to Workspace**
3. Review permissions and click **Allow**
4. Copy the **Bot User OAuth Token** (starts with `xoxb-`)
5. Save to `.env` as `SLACK_BOT_TOKEN`

### Enable Socket Mode (for Slash Commands)

1. Navigate to **Socket Mode**
2. Enable Socket Mode
3. Generate an **App-Level Token** with scope `connections:write`
4. Copy the token (starts with `xapp-`)
5. Save to `.env` as `SLACK_APP_TOKEN`

### Configure Slash Commands

1. Navigate to **Slash Commands**
2. Click **Create New Command**
3. Create the following commands:

| Command | Request URL | Short Description |
|---------|-------------|-------------------|
| `/summarize` | (Socket Mode - no URL needed) | Summarize knowledge on a topic |
| `/search` | (Socket Mode - no URL needed) | Semantic search across sources |
| `/digest` | (Socket Mode - no URL needed) | Get time-based digest |

### Get Signing Secret

1. Navigate to **Basic Information**
2. Scroll to **App Credentials**
3. Copy **Signing Secret**
4. Save to `.env` as `SLACK_SIGNING_SECRET`

### Test Connection

```bash
python -c "from api.slack_client import SlackClient; print('✅' if SlackClient().test_connection() else '❌')"
```

---

## 2. Notion API Setup

### Create Notion Integration

1. Go to [Notion Integrations](https://www.notion.so/my-integrations)
2. Click **New integration**
3. Enter integration name: "Knowledge Summarizer Agent"
4. Select associated workspace
5. Set capabilities:
   - ✅ Read content
   - ❌ Update content (not needed)
   - ❌ Insert content (not needed)
6. Click **Submit**
7. Copy the **Internal Integration Token** (starts with `secret_`)
8. Save to `.env` as `NOTION_API_KEY`

### Share Pages/Databases with Integration

1. Open Notion workspace
2. Navigate to the page or database you want to index
3. Click **Share** button (top right)
4. Click **Invite**
5. Search for "Knowledge Summarizer Agent"
6. Select the integration and click **Invite**

### Get Database ID (Optional)

If you want to index a specific database:

1. Open the database in Notion
2. Copy the URL: `https://notion.so/workspace/DATABASE_ID?v=...`
3. Extract `DATABASE_ID` from the URL
4. Save to `.env` as `NOTION_DATABASE_ID`

### Test Connection

```bash
python -c "from api.notion_client import NotionClient; print('✅' if NotionClient().test_connection() else '❌')"
```

---

## 3. Google Drive API Setup

### Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click **Select a project** → **New Project**
3. Enter project name: "Knowledge Summarizer Agent"
4. Click **Create**

### Enable Google Drive API

1. Navigate to **APIs & Services** → **Library**
2. Search for "Google Drive API"
3. Click **Google Drive API**
4. Click **Enable**

### Create Service Account

1. Navigate to **IAM & Admin** → **Service Accounts**
2. Click **Create Service Account**
3. Enter details:
   - Name: `knowledge-summarizer-sa`
   - ID: `knowledge-summarizer-sa`
   - Description: "Service account for Knowledge Summarizer Agent"
4. Click **Create and Continue**
5. Skip granting roles (not needed)
6. Click **Done**

### Generate Service Account Key

1. Click on the created service account
2. Go to **Keys** tab
3. Click **Add Key** → **Create new key**
4. Select **JSON** format
5. Click **Create**
6. Save the downloaded JSON file as `credentials/google-service-account.json`
7. Update `.env`:
   ```
   GOOGLE_APPLICATION_CREDENTIALS=./credentials/google-service-account.json
   ```

### Share Drive Folder with Service Account

1. Open Google Drive
2. Create or navigate to the folder you want to index
3. Right-click → **Share**
4. Paste the service account email (from JSON file):
   `knowledge-summarizer-sa@PROJECT_ID.iam.gserviceaccount.com`
5. Set permission: **Viewer**
6. Uncheck "Notify people"
7. Click **Share**
8. Copy the folder ID from URL:
   `https://drive.google.com/drive/folders/FOLDER_ID`
9. Save to `.env` as `GOOGLE_DRIVE_FOLDER_ID`

### Test Connection

```bash
python -c "from api.drive_client import DriveClient; print('✅' if DriveClient().test_connection() else '❌')"
```

---

## 4. Pinecone Setup

### Create Pinecone Account

1. Go to [Pinecone](https://www.pinecone.io/)
2. Sign up for free tier (sufficient for pilot)
3. Verify email and log in

### Create Index

1. Navigate to **Indexes**
2. Click **Create Index**
3. Enter details:
   - **Name**: `knowledge-summarizer`
   - **Dimensions**: `1536` (OpenAI ada-002)
   - **Metric**: `cosine`
   - **Environment**: `us-west1-gcp` (or closest region)
4. Click **Create Index**

### Get API Key

1. Navigate to **API Keys**
2. Copy the API key
3. Save to `.env` as `PINECONE_API_KEY`
4. Note the environment (e.g., `us-west1-gcp`)
5. Save to `.env` as `PINECONE_ENVIRONMENT`

### Test Connection

```bash
python -c "import pinecone; pinecone.init(api_key='YOUR_KEY', environment='YOUR_ENV'); print('✅' if len(pinecone.list_indexes()) >= 0 else '❌')"
```

---

## 5. OpenAI API Setup

### Get API Key

1. Go to [OpenAI Platform](https://platform.openai.com/)
2. Sign up or log in
3. Navigate to **API Keys**
4. Click **Create new secret key**
5. Copy the key (starts with `sk-`)
6. Save to `.env` as `OPENAI_API_KEY`

### Set Usage Limits

1. Navigate to **Billing** → **Usage limits**
2. Set monthly budget: $30
3. Enable email alerts at 80% usage

### Test Connection

```bash
python -c "from openai import OpenAI; client = OpenAI(); print('✅' if client.models.list() else '❌')"
```

---

## 6. Anthropic API Setup (Claude)

### Get API Key

1. Go to [Anthropic Console](https://console.anthropic.com/)
2. Sign up or log in
3. Navigate to **API Keys**
4. Click **Create Key**
5. Copy the key (starts with `sk-ant-`)
6. Save to `.env` as `ANTHROPIC_API_KEY`

### Set Usage Limits

1. Navigate to **Billing**
2. Set monthly budget: $20
3. Enable usage alerts

### Test Connection

```bash
python -c "from anthropic import Anthropic; client = Anthropic(); print('✅' if client.messages.create(model='claude-sonnet-4-5-20250929', max_tokens=10, messages=[{'role': 'user', 'content': 'Hi'}]) else '❌')"
```

---

## Complete .env File

After completing all setups, your `.env` file should look like:

```bash
# Slack
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...
SLACK_SIGNING_SECRET=...

# Notion
NOTION_API_KEY=secret_...
NOTION_DATABASE_ID=...

# Google Drive
GOOGLE_APPLICATION_CREDENTIALS=./credentials/google-service-account.json
GOOGLE_DRIVE_FOLDER_ID=...

# Pinecone
PINECONE_API_KEY=...
PINECONE_ENVIRONMENT=us-west1-gcp
PINECONE_INDEX_NAME=knowledge-summarizer

# OpenAI
OPENAI_API_KEY=sk-...

# Anthropic
ANTHROPIC_API_KEY=sk-ant-...
```

---

## Verification

Run all connection tests:

```bash
python scripts/export_samples.py
```

This will test all API connections and export sample data.

---

## Troubleshooting

### Slack: "invalid_auth" Error
- Verify token starts with `xoxb-`
- Ensure app is installed to workspace
- Check token hasn't expired

### Notion: "unauthorized" Error
- Verify integration is shared with pages/databases
- Check token starts with `secret_`
- Ensure workspace has correct permissions

### Google Drive: "insufficient permissions" Error
- Verify service account email is shared with folder
- Check JSON credentials file path is correct
- Ensure Drive API is enabled in GCP project

### Pinecone: Connection timeout
- Verify environment matches your index region
- Check API key is valid
- Ensure index name is correct

### OpenAI/Anthropic: Rate limit errors
- Check billing is set up
- Verify usage limits aren't exceeded
- Ensure API key is active

---

## Security Best Practices

1. **Never commit `.env` file** - Add to `.gitignore`
2. **Rotate API keys** - Every 90 days minimum
3. **Use least privilege** - Only grant necessary permissions
4. **Monitor usage** - Set up billing alerts
5. **Audit access logs** - Review monthly

---

## Next Steps

Once all APIs are configured:

1. Run sample export: `python scripts/export_samples.py`
2. Run data audit: `python scripts/data_audit.py`
3. Review compliance: See [COMPLIANCE.md](COMPLIANCE.md)
4. Deploy infrastructure: See [ARCHITECTURE.md](ARCHITECTURE.md)
