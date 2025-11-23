# Weekly Digest Generator
# Triggered by Cloud Scheduler to generate and post weekly knowledge summaries

import os
import json
from datetime import datetime, timedelta
from typing import List, Dict
import anthropic
from slack_sdk import WebClient
import structlog

logger = structlog.get_logger()


def generate_weekly_digest(event, context):
    """
    Cloud Function triggered weekly by Cloud Scheduler.
    Generates a digest of top updates from the past week and posts to #general.
    
    Args:
        event: Cloud Scheduler event
        context: Event context
    """
    try:
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent))
        
        from storage.pinecone_store import PineconeStore
        
        logger.info("weekly_digest_generation_started")
        
        # Initialize services
        vector_store = PineconeStore()
        claude_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        slack_client = WebClient(token=os.getenv("SLACK_BOT_TOKEN"))
        
        # Get stats from past week
        stats = vector_store.get_index_stats()
        
        # Query for recent high-relevance content across all namespaces
        # Using a generic "updates" query to find recent content
        from processing.embedder import Embedder
        embedder = Embedder()
        
        query_embedding = embedder.embed_text("important updates and changes")
        
        if not query_embedding:
            logger.error("failed_to_generate_query_embedding")
            return {"status": "error"}
        
        # Get top content from each source
        recent_content = vector_store.query_all_namespaces(
            vector=query_embedding.vector,
            top_k=10
        )
        
        # Prepare content for summarization
        content_pieces = []
        for source, results in recent_content.items():
            for result in results[:5]:  # Top 5 from each source
                metadata = result.get("metadata", {})
                content_pieces.append({
                    "source": source,
                    "content": metadata.get("content", ""),
                    "timestamp": metadata.get("timestamp", ""),
                    "url": metadata.get("url")
                })
        
        # Generate digest with Claude
        digest_text = _generate_digest_summary(claude_client, content_pieces)
        
        # Format and post to Slack
        slack_message = _format_digest_message(digest_text, stats)
        
        response = slack_client.chat_postMessage(
            channel=os.getenv("SLACK_GENERAL_CHANNEL", "#general"),
            text=slack_message,
            mrkdwn=True
        )
        
        logger.info(
            "weekly_digest_posted",
            channel=response["channel"],
            timestamp=response["ts"]
        )
        
        return {"status": "success", "items_processed": len(content_pieces)}
        
    except Exception as e:
        logger.error("weekly_digest_failed", error=str(e))
        return {"status": "error", "message": str(e)}


def _generate_digest_summary(
    claude_client: anthropic.Anthropic,
    content_pieces: List[Dict]
) -> str:
    """Generate weekly digest summary using Claude."""
    
    context = "\n\n".join([
        f"Source: {piece['source']}\nDate: {piece.get('timestamp', 'N/A')}\nContent: {piece['content'][:300]}"
        for piece in content_pieces[:10]
    ])
    
    prompt = f"""Based on the following knowledge base updates from the past week, create a concise weekly digest highlighting the top 5 most important updates or themes.

Recent Updates:
{context}

Instructions:
- Identify the 5 most significant topics or themes
- Provide a brief (1-2 sentence) summary for each
- Group related updates together
- Use bullet points for clarity
- Keep the total digest to ~200 words

Weekly Digest:"""
    
    try:
        message = claude_client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}]
        )
        
        return message.content[0].text
        
    except Exception as e:
        logger.error("digest_generation_failed", error=str(e))
        return "Unable to generate digest summary."


def _format_digest_message(digest: str, stats: Dict) -> str:
    """Format digest for Slack posting."""
    
    current_date = datetime.utcnow()
    week_ago = current_date - timedelta(days=7)
    
    message = f"""📊 *Weekly Knowledge Digest* | {week_ago.strftime('%b %d')} - {current_date.strftime('%b %d, %Y')}

{digest}

_Knowledge Base Stats:_
• Total Documents: {stats.get('total_vector_count', 'N/A'):,}
• Sources: Slack, Notion, Google Drive

💡 Use `/summarize [your question]` to search the knowledge base anytime!
"""
    
    return message


if __name__ == "__main__":
    # Test locally
    from dotenv import load_dotenv
    load_dotenv()
    
    result = generate_weekly_digest(None, None)
    print(f"Digest generation result: {result}")
