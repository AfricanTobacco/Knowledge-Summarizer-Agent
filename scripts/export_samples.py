"""
Export sample data from Slack, Notion, and Google Drive for audit.
"""
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.slack_client import SlackClient
from api.notion_client import NotionClient
from api.drive_client import DriveClient
from dotenv import load_dotenv
import structlog

logger = structlog.get_logger()

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer()
    ]
)


def export_slack_samples(num_messages: int = 500):
    """Export sample Slack messages."""
    print(f"\n📨 Exporting {num_messages} Slack messages...")
    try:
        client = SlackClient()
        if not client.test_connection():
            print("❌ Slack connection failed")
            return False

        messages = client.export_sample_messages(
            num_messages=num_messages,
            output_file="sample_slack_messages.json"
        )
        print(f"✅ Exported {len(messages)} Slack messages")
        return True
    except Exception as e:
        print(f"❌ Slack export failed: {e}")
        logger.error("slack_export_failed", error=str(e))
        return False


def export_notion_samples(num_pages: int = 20):
    """Export sample Notion pages."""
    print(f"\n📄 Exporting {num_pages} Notion pages...")
    try:
        client = NotionClient()
        if not client.test_connection():
            print("❌ Notion connection failed")
            return False

        pages = client.export_sample_pages(
            num_pages=num_pages,
            output_file="sample_notion_pages.json"
        )
        print(f"✅ Exported {len(pages)} Notion pages")
        return True
    except Exception as e:
        print(f"❌ Notion export failed: {e}")
        logger.error("notion_export_failed", error=str(e))
        return False


def export_drive_samples(num_docs: int = 10):
    """Export sample Google Drive documents."""
    print(f"\n📁 Exporting {num_docs} Google Drive documents...")
    try:
        client = DriveClient()
        if not client.test_connection():
            print("❌ Google Drive connection failed")
            return False

        docs = client.export_sample_documents(
            num_docs=num_docs,
            output_file="sample_drive_docs.json"
        )
        print(f"✅ Exported {len(docs)} Drive documents")
        return True
    except Exception as e:
        print(f"❌ Drive export failed: {e}")
        logger.error("drive_export_failed", error=str(e))
        return False


def main():
    """Export all sample data."""
    print("=" * 60)
    print("Knowledge Summarizer Agent - Sample Data Export")
    print("=" * 60)

    # Load environment variables
    load_dotenv()

    # Check required env vars
    required_vars = [
        "SLACK_BOT_TOKEN",
        "NOTION_API_KEY",
        "GOOGLE_APPLICATION_CREDENTIALS"
    ]

    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        print("\n❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\nPlease set these in your .env file")
        return 1

    # Export samples from each source
    results = {
        "slack": export_slack_samples(num_messages=500),
        "notion": export_notion_samples(num_pages=20),
        "drive": export_drive_samples(num_docs=10)
    }

    # Summary
    print("\n" + "=" * 60)
    print("Export Summary")
    print("=" * 60)

    success_count = sum(1 for v in results.values() if v)
    total_count = len(results)

    for source, success in results.items():
        status = "✅ SUCCESS" if success else "❌ FAILED"
        print(f"  {source.capitalize()}: {status}")

    print(f"\nTotal: {success_count}/{total_count} successful")

    if success_count == total_count:
        print("\n🎉 All exports completed successfully!")
        print("\nNext steps:")
        print("  1. Run PII scan: python scripts/data_audit.py")
        print("  2. Review compliance: See docs/COMPLIANCE.md")
        return 0
    else:
        print("\n⚠️  Some exports failed. Check error messages above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
