"""
Slack bot for Knowledge Summarizer Agent.
Handles /summarize commands and provides semantic search results.
"""
import os
from typing import List, Dict, Optional
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import structlog
import anthropic

# Import our modules
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from processing.embedder import Embedder
from storage.pinecone_store import PineconeStore

logger = structlog.get_logger()


class KnowledgeBot:
    """Slack bot for knowledge summarization and retrieval."""
    
    def __init__(
        self,
        slack_bot_token: Optional[str] = None,
        slack_app_token: Optional[str] = None,
        anthropic_api_key: Optional[str] = None
    ):
        """
        Initialize Knowledge Bot.
        
        Args:
            slack_bot_token: Slack bot token
            slack_app_token: Slack app token (for socket mode)
            anthropic_api_key: Anthropic API key for Claude
        """
        self.slack_bot_token = slack_bot_token or os.getenv("SLACK_BOT_TOKEN")
        self.slack_app_token = slack_app_token or os.getenv("SLACK_APP_TOKEN")
        self.anthropic_api_key = anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")
        
        if not all([self.slack_bot_token, self.slack_app_token, self.anthropic_api_key]):
            raise ValueError("Missing required API tokens")
        
        # Initialize Slack app
        self.app = App(token=self.slack_bot_token)
        
        # Initialize services
        self.embedder = Embedder()
        self.vector_store = PineconeStore()
        self.claude = anthropic.Anthropic(api_key=self.anthropic_api_key)
        
        # Register command handlers
        self._register_handlers()
    
    def _register_handlers(self):
        """Register Slack command handlers."""
        
        @self.app.command("/summarize")
        def handle_summarize(ack, command, say):
            """Handle /summarize command."""
            ack()
            
            query_text = command.get("text", "").strip()
            user_id = command.get("user_id")
            channel_id = command.get("channel_id")
            
            logger.info(
                "summarize_command_received",
                user_id=user_id,
                channel_id=channel_id,
                query=query_text
            )
            
            if not query_text:
                say("❌ Please provide a search query. Example: `/summarize onboarding process`")
                return
            
            # Show loading message
            say(f"🔍 Searching for: *{query_text}*...")
            
            try:
                # Generate query embedding
                embedding_result = self.embedder.embed_text(query_text)
                
                if not embedding_result:
                    say("❌ Failed to process query. Please try again.")
                    return
                
                # Search across all namespaces
                results = self.vector_store.query_all_namespaces(
                    vector=embedding_result.vector,
                    top_k=5
                )
                
                if not results:
                    say(f"🤷 No results found for: *{query_text}*")
                    return
                
                # Collect context from results
                context_chunks = []
                for source, matches in results.items():
                    for match in matches:
                        metadata = match.get("metadata", {})
                        content = metadata.get("content", "")
                        if content:
                            context_chunks.append({
                                "source": source,
                                "content": content,
                                "score": match.get("score", 0),
                                "url": metadata.get("url"),
                                "timestamp": metadata.get("timestamp")
                            })
                
                # Generate summary with Claude
                summary = self._generate_summary(query_text, context_chunks)
                
                # Format response
                response = self._format_response(query_text, summary, context_chunks)
                say(response)
                
                logger.info(
                    "summarize_command_completed",
                    user_id=user_id,
                    results_count=len(context_chunks)
                )
                
            except Exception as e:
                logger.error("summarize_command_failed", error=str(e))
                say(f"❌ An error occurred: {str(e)}")
        
        @self.app.event("app_mention")
        def handle_mention(event, say):
            """Handle bot mentions."""
            text = event.get("text", "")
            user = event.get("user")
            
            logger.info("bot_mentioned", user=user, text=text)
            
            say(
                f"👋 Hi <@{user}>! Use `/summarize [your question]` to search the knowledge base.\n"
                f"Example: `/summarize how do I onboard a new client?`"
            )
    
    def _generate_summary(
        self,
        query: str,
        context_chunks: List[Dict]
    ) -> str:
        """
        Generate summary using Claude.
        
        Args:
            query: User query
            context_chunks: Retrieved context chunks
            
        Returns:
            Generated summary
        """
        if not context_chunks:
            return "No relevant information found."
        
        # Prepare context for Claude
        context_text = "\n\n".join([
            f"Source: {chunk['source']}\nContent: {chunk['content'][:500]}"
            for chunk in context_chunks[:5]
        ])
        
        prompt = f"""Based on the following knowledge base excerpts, provide a concise and helpful answer to the user's question.

User Question: {query}

Relevant Information:
{context_text}

Instructions:
- Provide a direct, actionable answer
- If multiple sources agree, synthesize them
- If sources conflict, note the different perspectives
- Keep the response concise (2-3 paragraphs max)
- If the information doesn't fully answer the question, acknowledge that

Answer:"""
        
        try:
            message = self.claude.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=500,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )
            
            summary = message.content[0].text
            
            logger.info("summary_generated", model="claude-3-haiku")
            return summary
            
        except Exception as e:
            logger.error("summary_generation_failed", error=str(e))
            return "Failed to generate summary. Please try again."
    
    def _format_response(
        self,
        query: str,
        summary: str,
        context_chunks: List[Dict]
    ) -> str:
        """
        Format bot response.
        
        Args:
            query: Original query
            summary: Generated summary
            context_chunks: Context chunks used
            
        Returns:
            Formatted response string
        """
        response_parts = [
            f"📚 *Knowledge Base Results for:* _{query}_\n",
            summary,
            "\n*Sources:*"
        ]
        
        # Add top sources
        for i, chunk in enumerate(context_chunks[:3], 1):
            source_line = f"{i}. {chunk['source'].title()}"
            if chunk.get('url'):
                source_line += f" - <{chunk['url']}|Link>"
            if chunk.get('timestamp'):
                source_line += f" ({chunk['timestamp'][:10]})"
            response_parts.append(source_line)
        
        return "\n".join(response_parts)
    
    def start(self):
        """Start the bot in socket mode."""
        logger.info("starting_knowledge_bot")
        handler = SocketModeHandler(self.app, self.slack_app_token)
        handler.start()


if __name__ == "__main__":
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Start bot
    bot = KnowledgeBot()
    bot.start()
