# Credentials Setup Guide

This document explains the different ways to configure API credentials for the Knowledge Summarizer Agent.

## Setup Options

### Option 1: Local Development (Recommended for Testing)

**Use when**: Running locally for development and testing

**Script**: `setup-local-env.ps1`

**Steps**:
```powershell
# Run the interactive setup script
.\setup-local-env.ps1
```

This will:
1. Prompt you for all API credentials
2. Create a `.env` file in the project root
3. Copy your GCP service account JSON to `credentials/` folder
4. Set up all required environment variables

**Pros**:
- ✅ Quick and easy for local development
- ✅ No AWS dependencies
- ✅ Works offline

**Cons**:
- ❌ Not suitable for production
- ❌ Credentials stored in plaintext on disk
- ❌ Need to manually share with team

---

### Option 2: AWS Secrets Manager (Recommended for Production)

**Use when**: Deploying to production or sharing credentials with team

**Script**: `setup-aws-secrets.ps1`

**Prerequisites**:
- AWS CLI installed and configured
- AWS account with Secrets Manager permissions

**Steps**:

1. **Store secrets in AWS**:
   ```powershell
   # Upload all credentials to AWS Secrets Manager
   .\setup-aws-secrets.ps1
   ```

2. **Load secrets locally**:
   ```powershell
   # Download secrets from AWS and create .env file
   .\load-secrets-from-aws.ps1
   ```

**Secrets Created**:
- `knowledge-summarizer-slack` - Slack API credentials
- `knowledge-summarizer-notion` - Notion API key
- `knowledge-summarizer-gcp-service-account` - GCP service account JSON
- `knowledge-summarizer-pinecone` - Pinecone vector DB credentials
- `knowledge-summarizer-openai` - OpenAI API key
- `knowledge-summarizer-anthropic` - Claude API key

**Pros**:
- ✅ Secure storage with encryption at rest
- ✅ Easy to share with team (no plaintext sharing)
- ✅ Audit logs for access
- ✅ Automatic rotation support
- ✅ Works with Lambda/production deployments

**Cons**:
- ❌ Requires AWS account and permissions
- ❌ Small cost (~$0.40/month per secret)
- ❌ Requires internet connection

---

### Option 3: Manual Setup

**Use when**: You want full control or have existing credentials

**Steps**:

1. Copy the example file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` with your favorite editor:
   ```bash
   code .env  # VS Code
   # or
   notepad .env  # Notepad
   ```

3. Fill in all the values following the comments in the file

4. Save your GCP service account JSON to:
   ```
   credentials/google-service-account.json
   ```

---

## Credential Sources

### Where to Get API Keys

| Service | Where to Get | Format | Docs |
|---------|-------------|--------|------|
| **Slack** | [api.slack.com/apps](https://api.slack.com/apps) | `xoxb-...` | [API Setup Guide](API_SETUP.md#1-slack-api-setup) |
| **Notion** | [notion.so/my-integrations](https://www.notion.so/my-integrations) | `secret_...` | [API Setup Guide](API_SETUP.md#2-notion-api-setup) |
| **Google Drive** | [console.cloud.google.com](https://console.cloud.google.com) | JSON file | [API Setup Guide](API_SETUP.md#3-google-drive-api-setup) |
| **Pinecone** | [app.pinecone.io](https://app.pinecone.io) | Random string | [API Setup Guide](API_SETUP.md#4-pinecone-setup) |
| **OpenAI** | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) | `sk-...` | [API Setup Guide](API_SETUP.md#5-openai-api-setup) |
| **Anthropic** | [console.anthropic.com](https://console.anthropic.com) | `sk-ant-...` | [API Setup Guide](API_SETUP.md#6-anthropic-api-setup) |

---

## Verification

After setting up credentials with any method, verify they work:

### Test Individual APIs

```powershell
# Test Slack
python -c "from api.slack_client import SlackClient; print('✅ Slack OK' if SlackClient().test_connection() else '❌ Slack FAILED')"

# Test Notion
python -c "from api.notion_client import NotionClient; print('✅ Notion OK' if NotionClient().test_connection() else '❌ Notion FAILED')"

# Test Google Drive
python -c "from api.drive_client import DriveClient; print('✅ Drive OK' if DriveClient().test_connection() else '❌ Drive FAILED')"
```

### Test All APIs

```powershell
# This will test all APIs and export sample data
python scripts/export_samples.py
```

Expected output:
```
✅ Exported 500 Slack messages
✅ Exported 20 Notion pages
✅ Exported 10 Drive documents
```

---

## Security Best Practices

### 1. Never Commit Credentials

The `.gitignore` file already excludes:
- `.env` files
- `credentials/` folder
- `*.json` files (except specific config files)

**Always verify before committing**:
```bash
git status
# Check that .env and credentials/ are NOT listed
```

### 2. Rotate Keys Regularly

Set a calendar reminder to rotate keys every 90 days:

| Service | Rotation Steps |
|---------|---------------|
| Slack | Regenerate token in Slack app settings |
| Notion | Create new integration, update key |
| Google Drive | Create new service account key, delete old |
| OpenAI | Create new key, revoke old |
| Anthropic | Create new key, revoke old |
| Pinecone | Rotate API key in dashboard |

After rotation:
1. Update AWS Secrets Manager: `.\setup-aws-secrets.ps1`
2. Or update `.env` file manually
3. Restart any running services

### 3. Use Least Privilege

Ensure each API key has minimum required permissions:

- **Slack**: Read-only scopes (no write unless needed)
- **Notion**: Read content only
- **Google Drive**: Viewer role on shared folders
- **OpenAI/Anthropic**: Set usage limits
- **Pinecone**: Read/write access to specific index only

### 4. Monitor Usage

Set up billing alerts:

| Service | Monthly Budget | Alert Threshold |
|---------|---------------|-----------------|
| OpenAI | $30 | 80% ($24) |
| Anthropic | $20 | 80% ($16) |
| Pinecone | $7 | 100% |
| **Total** | **$57** | **~$50** |

### 5. Secure Local Environment

- Use full disk encryption (BitLocker/FileVault)
- Lock your computer when away
- Don't share screenshots containing credentials
- Use password manager for credential storage

---

## Troubleshooting

### "Secret not found" when loading from AWS

**Solution**:
1. Verify you're using the correct region:
   ```powershell
   .\load-secrets-from-aws.ps1 -Region us-west-2
   ```

2. Check secrets exist:
   ```bash
   aws secretsmanager list-secrets --region us-west-2
   ```

3. Ensure you have correct permissions:
   ```bash
   aws sts get-caller-identity
   ```

### "Invalid authentication" errors

**For Slack**:
- Verify token starts with `xoxb-` (bot token, not user token)
- Check app is installed to workspace
- Regenerate token if expired

**For Notion**:
- Verify token starts with `secret_`
- Ensure integration is shared with pages/databases
- Check workspace permissions

**For Google Drive**:
- Verify service account email is shared with folder
- Check JSON credentials file is valid
- Ensure Drive API is enabled in GCP project

### GCP service account JSON not found

**Solution**:
1. Verify file exists:
   ```powershell
   Test-Path credentials/google-service-account.json
   ```

2. Check file permissions (must be readable)

3. Ensure `GOOGLE_APPLICATION_CREDENTIALS` path is correct in `.env`:
   ```
   GOOGLE_APPLICATION_CREDENTIALS=./credentials/google-service-account.json
   ```

---

## Team Workflows

### For Team Jerome (Infrastructure)

1. **Initial Setup**:
   ```powershell
   # Store credentials in AWS Secrets Manager (one time)
   .\setup-aws-secrets.ps1 -Region us-west-2
   ```

2. **Team Members**:
   ```powershell
   # Each team member loads from AWS
   .\load-secrets-from-aws.ps1 -Region us-west-2
   ```

3. **Lambda/Production**:
   - Reference secrets by ARN in Terraform
   - Use IAM roles for access (no hardcoded keys)

### For Team Mako (Compliance)

1. **Audit Credentials**:
   ```bash
   # List all secrets
   aws secretsmanager list-secrets --region us-west-2

   # Check last rotation date
   aws secretsmanager describe-secret --secret-id knowledge-summarizer-slack
   ```

2. **Review Access Logs**:
   ```bash
   # CloudTrail logs for secret access
   aws cloudtrail lookup-events \
     --lookup-attributes AttributeKey=ResourceName,AttributeValue=knowledge-summarizer-slack
   ```

---

## Migration from Daily Coordinator

If you already have credentials set up for the Daily Coordinator:

1. The Slack webhook from Daily Coordinator can be reused:
   ```bash
   aws secretsmanager get-secret-value \
     --secret-id daily-coordinator-slack-webhook \
     --region us-west-2
   ```

2. Copy the webhook URL to the Knowledge Summarizer setup

3. Or reference the same secret in both applications (shared credentials)

---

## References

- [API Setup Guide](API_SETUP.md) - Detailed API credential creation steps
- [AWS Secrets Manager](https://aws.amazon.com/secrets-manager/)
- [POPIA Compliance](COMPLIANCE.md) - Data protection requirements
- [Architecture](ARCHITECTURE.md) - How credentials are used in production

---

## Quick Reference

### Setup Scripts

| Script | Purpose | When to Use |
|--------|---------|-------------|
| `setup-local-env.ps1` | Create local `.env` file | Local development |
| `setup-aws-secrets.ps1` | Upload to AWS Secrets Manager | Production/team sharing |
| `load-secrets-from-aws.ps1` | Download from AWS to `.env` | New team member setup |

### Commands

```powershell
# Local setup (interactive)
.\setup-local-env.ps1

# AWS setup (upload credentials)
.\setup-aws-secrets.ps1 -Region us-west-2

# AWS load (download credentials)
.\load-secrets-from-aws.ps1 -Region us-west-2

# Verify setup
python scripts/export_samples.py

# Run audit
python scripts/data_audit.py
```
