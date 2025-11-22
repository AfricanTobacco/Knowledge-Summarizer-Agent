"""
Slack API client for message retrieval and bot interactions.
"""
import os
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import structlog

logger = structlog.get_logger()


class SlackClient:
    """Client for interacting with Slack API."""

    def __init__(self, token: Optional[str] = None):
        """
        Initialize Slack client.

        Args:
            token: Slack bot token. If not provided, reads from SLACK_BOT_TOKEN env var.
        """
        self.token = token or os.getenv("SLACK_BOT_TOKEN")
        if not self.token:
            raise ValueError("SLACK_BOT_TOKEN must be set")

        self.client = WebClient(token=self.token)
        self.workspace_id = os.getenv("SLACK_WORKSPACE_ID")

    def test_connection(self) -> bool:
        """
        Test Slack API connection.

        Returns:
            True if connection successful, False otherwise.
        """
        try:
            response = self.client.auth_test()
            logger.info("slack_connection_test_success", team=response["team"])
            return True
        except SlackApiError as e:
            logger.error("slack_connection_test_failed", error=str(e))
            return False

    def get_channels(self, limit: int = 100) -> List[Dict]:
        """
        Retrieve list of channels.

        Args:
            limit: Maximum number of channels to retrieve.

        Returns:
            List of channel dictionaries.
        """
        try:
            response = self.client.conversations_list(
                limit=limit,
                exclude_archived=True,
                types="public_channel,private_channel"
            )
            channels = response["channels"]
            logger.info("slack_channels_retrieved", count=len(channels))
            return channels
        except SlackApiError as e:
            logger.error("slack_channels_retrieval_failed", error=str(e))
            return []

    def get_messages(
        self,
        channel_id: str,
        limit: int = 500,
        days_back: int = 30
    ) -> List[Dict]:
        """
        Retrieve messages from a channel.

        Args:
            channel_id: Channel ID to retrieve messages from.
            limit: Maximum number of messages to retrieve.
            days_back: Number of days to look back for messages.

        Returns:
            List of message dictionaries.
        """
        try:
            oldest = (datetime.now() - timedelta(days=days_back)).timestamp()

            response = self.client.conversations_history(
                channel=channel_id,
                limit=limit,
                oldest=oldest
            )

            messages = response["messages"]
            logger.info(
                "slack_messages_retrieved",
                channel=channel_id,
                count=len(messages)
            )
            return messages
        except SlackApiError as e:
            logger.error(
                "slack_messages_retrieval_failed",
                channel=channel_id,
                error=str(e)
            )
            return []

    def get_thread_replies(
        self,
        channel_id: str,
        thread_ts: str
    ) -> List[Dict]:
        """
        Retrieve replies in a thread.

        Args:
            channel_id: Channel ID containing the thread.
            thread_ts: Thread timestamp.

        Returns:
            List of reply message dictionaries.
        """
        try:
            response = self.client.conversations_replies(
                channel=channel_id,
                ts=thread_ts
            )
            replies = response["messages"]
            logger.info(
                "slack_thread_replies_retrieved",
                channel=channel_id,
                thread_ts=thread_ts,
                count=len(replies)
            )
            return replies
        except SlackApiError as e:
            logger.error(
                "slack_thread_replies_failed",
                channel=channel_id,
                thread_ts=thread_ts,
                error=str(e)
            )
            return []

    def get_user_info(self, user_id: str) -> Optional[Dict]:
        """
        Retrieve user information.

        Args:
            user_id: User ID to retrieve info for.

        Returns:
            User info dictionary or None if not found.
        """
        try:
            response = self.client.users_info(user=user_id)
            return response["user"]
        except SlackApiError as e:
            logger.error("slack_user_info_failed", user_id=user_id, error=str(e))
            return None

    def export_sample_messages(
        self,
        num_messages: int = 500,
        output_file: str = "sample_slack_messages.json"
    ) -> List[Dict]:
        """
        Export sample messages for data audit.

        Args:
            num_messages: Number of messages to export.
            output_file: Output file path.

        Returns:
            List of exported messages.
        """
        import json

        all_messages = []
        channels = self.get_channels()

        messages_per_channel = max(1, num_messages // len(channels)) if channels else num_messages

        for channel in channels:
            if len(all_messages) >= num_messages:
                break

            messages = self.get_messages(
                channel_id=channel["id"],
                limit=messages_per_channel
            )

            for msg in messages:
                if len(all_messages) >= num_messages:
                    break

                # Include basic metadata without PII exposure
                all_messages.append({
                    "channel_id": channel["id"],
                    "channel_name": channel.get("name", "unknown"),
                    "timestamp": msg.get("ts"),
                    "text": msg.get("text", ""),
                    "thread_ts": msg.get("thread_ts"),
                    "user_id": msg.get("user", "unknown")
                })

        # Save to file
        with open(output_file, "w") as f:
            json.dump(all_messages, f, indent=2)

        logger.info(
            "slack_sample_export_complete",
            count=len(all_messages),
            output_file=output_file
        )

        return all_messages


if __name__ == "__main__":
    # Test the client
    from dotenv import load_dotenv
    load_dotenv()

    client = SlackClient()
    if client.test_connection():
        print("✅ Slack API connection successful")

        # Get sample channels
        channels = client.get_channels(limit=5)
        print(f"✅ Retrieved {len(channels)} channels")

        # Export sample messages
        messages = client.export_sample_messages(num_messages=10)
        print(f"✅ Exported {len(messages)} sample messages")
    else:
        print("❌ Slack API connection failed")
