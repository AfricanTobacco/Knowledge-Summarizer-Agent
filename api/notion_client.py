"""
Notion API client for page and database retrieval.
"""
import os
from typing import List, Dict, Optional
from notion_client import Client
import structlog

logger = structlog.get_logger()


class NotionClient:
    """Client for interacting with Notion API."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Notion client.

        Args:
            api_key: Notion integration token. If not provided, reads from NOTION_API_KEY env var.
        """
        self.api_key = api_key or os.getenv("NOTION_API_KEY")
        if not self.api_key:
            raise ValueError("NOTION_API_KEY must be set")

        self.client = Client(auth=self.api_key)
        self.database_id = os.getenv("NOTION_DATABASE_ID")

    def test_connection(self) -> bool:
        """
        Test Notion API connection.

        Returns:
            True if connection successful, False otherwise.
        """
        try:
            # List users to test connection
            self.client.users.list()
            logger.info("notion_connection_test_success")
            return True
        except Exception as e:
            logger.error("notion_connection_test_failed", error=str(e))
            return False

    def search_pages(
        self,
        query: str = "",
        page_size: int = 100
    ) -> List[Dict]:
        """
        Search for pages in Notion.

        Args:
            query: Search query string.
            page_size: Maximum number of results.

        Returns:
            List of page dictionaries.
        """
        try:
            response = self.client.search(
                query=query,
                page_size=page_size,
                filter={"property": "object", "value": "page"}
            )
            pages = response.get("results", [])
            logger.info("notion_pages_retrieved", count=len(pages))
            return pages
        except Exception as e:
            logger.error("notion_search_failed", error=str(e))
            return []

    def get_page_content(self, page_id: str) -> Dict:
        """
        Retrieve page content including blocks.

        Args:
            page_id: Notion page ID.

        Returns:
            Dictionary containing page metadata and blocks.
        """
        try:
            # Get page metadata
            page = self.client.pages.retrieve(page_id=page_id)

            # Get page blocks (content)
            blocks_response = self.client.blocks.children.list(block_id=page_id)
            blocks = blocks_response.get("results", [])

            content = {
                "page_id": page_id,
                "title": self._extract_title(page),
                "properties": page.get("properties", {}),
                "blocks": blocks,
                "created_time": page.get("created_time"),
                "last_edited_time": page.get("last_edited_time")
            }

            logger.info("notion_page_content_retrieved", page_id=page_id)
            return content
        except Exception as e:
            logger.error("notion_page_content_failed", page_id=page_id, error=str(e))
            return {}

    def get_database_pages(
        self,
        database_id: Optional[str] = None,
        page_size: int = 100
    ) -> List[Dict]:
        """
        Query pages from a database.

        Args:
            database_id: Database ID to query. Uses default if not provided.
            page_size: Maximum number of results.

        Returns:
            List of page dictionaries.
        """
        db_id = database_id or self.database_id
        if not db_id:
            logger.error("notion_database_id_missing")
            return []

        try:
            response = self.client.databases.query(
                database_id=db_id,
                page_size=page_size
            )
            pages = response.get("results", [])
            logger.info("notion_database_pages_retrieved", count=len(pages))
            return pages
        except Exception as e:
            logger.error("notion_database_query_failed", error=str(e))
            return []

    def _extract_title(self, page: Dict) -> str:
        """
        Extract title from page properties.

        Args:
            page: Page dictionary.

        Returns:
            Page title string.
        """
        properties = page.get("properties", {})

        # Try common title property names
        for prop_name in ["Name", "Title", "title", "name"]:
            if prop_name in properties:
                title_prop = properties[prop_name]
                if title_prop.get("type") == "title":
                    title_array = title_prop.get("title", [])
                    if title_array:
                        return title_array[0].get("plain_text", "Untitled")

        return "Untitled"

    def _extract_text_from_blocks(self, blocks: List[Dict]) -> str:
        """
        Extract plain text from Notion blocks.

        Args:
            blocks: List of block dictionaries.

        Returns:
            Combined plain text.
        """
        text_parts = []

        for block in blocks:
            block_type = block.get("type")
            if not block_type:
                continue

            block_content = block.get(block_type, {})

            # Extract text from rich text arrays
            if "rich_text" in block_content:
                for text_obj in block_content["rich_text"]:
                    text_parts.append(text_obj.get("plain_text", ""))

            # Handle other block types
            elif "text" in block_content:
                text_parts.append(block_content["text"])

        return "\n".join(text_parts)

    def export_sample_pages(
        self,
        num_pages: int = 20,
        output_file: str = "sample_notion_pages.json"
    ) -> List[Dict]:
        """
        Export sample pages for data audit.

        Args:
            num_pages: Number of pages to export.
            output_file: Output file path.

        Returns:
            List of exported pages.
        """
        import json

        pages = self.search_pages(page_size=num_pages)
        exported_pages = []

        for page in pages[:num_pages]:
            page_id = page["id"]
            content = self.get_page_content(page_id)

            if content:
                # Extract text from blocks
                text_content = self._extract_text_from_blocks(content.get("blocks", []))

                exported_pages.append({
                    "page_id": page_id,
                    "title": content.get("title", "Untitled"),
                    "created_time": content.get("created_time"),
                    "last_edited_time": content.get("last_edited_time"),
                    "text_content": text_content,
                    "block_count": len(content.get("blocks", []))
                })

        # Save to file
        with open(output_file, "w") as f:
            json.dump(exported_pages, f, indent=2)

        logger.info(
            "notion_sample_export_complete",
            count=len(exported_pages),
            output_file=output_file
        )

        return exported_pages


if __name__ == "__main__":
    # Test the client
    from dotenv import load_dotenv
    load_dotenv()

    client = NotionClient()
    if client.test_connection():
        print("✅ Notion API connection successful")

        # Search for pages
        pages = client.search_pages(page_size=5)
        print(f"✅ Retrieved {len(pages)} pages")

        # Export sample pages
        sample_pages = client.export_sample_pages(num_pages=5)
        print(f"✅ Exported {len(sample_pages)} sample pages")
    else:
        print("❌ Notion API connection failed")
