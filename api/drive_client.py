"""
Google Drive API client for document retrieval.
"""
import os
import io
from typing import List, Dict, Optional
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2 import service_account
import structlog

logger = structlog.get_logger()


class DriveClient:
    """Client for interacting with Google Drive API."""

    SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

    def __init__(self, credentials_path: Optional[str] = None):
        """
        Initialize Google Drive client.

        Args:
            credentials_path: Path to service account credentials JSON file.
                            If not provided, reads from GOOGLE_APPLICATION_CREDENTIALS env var.
        """
        self.credentials_path = credentials_path or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if not self.credentials_path:
            raise ValueError("GOOGLE_APPLICATION_CREDENTIALS must be set")

        self.credentials = service_account.Credentials.from_service_account_file(
            self.credentials_path,
            scopes=self.SCOPES
        )

        self.service = build('drive', 'v3', credentials=self.credentials)
        self.folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")

    def test_connection(self) -> bool:
        """
        Test Google Drive API connection.

        Returns:
            True if connection successful, False otherwise.
        """
        try:
            about = self.service.about().get(fields="user").execute()
            logger.info("drive_connection_test_success", user=about.get("user", {}).get("emailAddress"))
            return True
        except Exception as e:
            logger.error("drive_connection_test_failed", error=str(e))
            return False

    def list_files(
        self,
        folder_id: Optional[str] = None,
        page_size: int = 100,
        mime_types: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        List files in a folder.

        Args:
            folder_id: Folder ID to list files from. Uses default if not provided.
            page_size: Maximum number of files to retrieve.
            mime_types: List of MIME types to filter by.

        Returns:
            List of file metadata dictionaries.
        """
        folder = folder_id or self.folder_id

        try:
            # Build query
            query_parts = []
            if folder:
                query_parts.append(f"'{folder}' in parents")

            if mime_types:
                mime_query = " or ".join([f"mimeType='{mt}'" for mt in mime_types])
                query_parts.append(f"({mime_query})")

            query = " and ".join(query_parts) if query_parts else None

            # Execute query
            results = self.service.files().list(
                q=query,
                pageSize=page_size,
                fields="files(id, name, mimeType, createdTime, modifiedTime, size, owners)"
            ).execute()

            files = results.get('files', [])
            logger.info("drive_files_listed", count=len(files))
            return files
        except Exception as e:
            logger.error("drive_list_files_failed", error=str(e))
            return []

    def get_file_content(self, file_id: str) -> Optional[str]:
        """
        Download and retrieve file content.

        Args:
            file_id: File ID to download.

        Returns:
            File content as string, or None if download fails.
        """
        try:
            # Get file metadata first
            file_metadata = self.service.files().get(fileId=file_id, fields="mimeType, name").execute()
            mime_type = file_metadata.get('mimeType')

            # Handle Google Docs export
            if mime_type == 'application/vnd.google-apps.document':
                request = self.service.files().export_media(
                    fileId=file_id,
                    mimeType='text/plain'
                )
            elif mime_type == 'application/vnd.google-apps.spreadsheet':
                request = self.service.files().export_media(
                    fileId=file_id,
                    mimeType='text/csv'
                )
            elif mime_type == 'application/vnd.google-apps.presentation':
                request = self.service.files().export_media(
                    fileId=file_id,
                    mimeType='text/plain'
                )
            else:
                # Download binary files
                request = self.service.files().get_media(fileId=file_id)

            # Download content
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)

            done = False
            while not done:
                status, done = downloader.next_chunk()

            content = fh.getvalue().decode('utf-8', errors='ignore')

            logger.info("drive_file_downloaded", file_id=file_id, size=len(content))
            return content
        except Exception as e:
            logger.error("drive_file_download_failed", file_id=file_id, error=str(e))
            return None

    def search_files(
        self,
        query: str,
        page_size: int = 100
    ) -> List[Dict]:
        """
        Search for files by name or content.

        Args:
            query: Search query string.
            page_size: Maximum number of results.

        Returns:
            List of file metadata dictionaries.
        """
        try:
            search_query = f"name contains '{query}' or fullText contains '{query}'"

            results = self.service.files().list(
                q=search_query,
                pageSize=page_size,
                fields="files(id, name, mimeType, createdTime, modifiedTime, size)"
            ).execute()

            files = results.get('files', [])
            logger.info("drive_search_complete", query=query, count=len(files))
            return files
        except Exception as e:
            logger.error("drive_search_failed", query=query, error=str(e))
            return []

    def export_sample_documents(
        self,
        num_docs: int = 10,
        output_file: str = "sample_drive_docs.json"
    ) -> List[Dict]:
        """
        Export sample documents for data audit.

        Args:
            num_docs: Number of documents to export.
            output_file: Output file path.

        Returns:
            List of exported documents.
        """
        import json

        # Get Google Docs, Sheets, and standard documents
        mime_types = [
            'application/vnd.google-apps.document',
            'application/vnd.google-apps.spreadsheet',
            'application/pdf',
            'text/plain'
        ]

        files = self.list_files(mime_types=mime_types, page_size=num_docs)
        exported_docs = []

        for file_metadata in files[:num_docs]:
            file_id = file_metadata['id']
            content = self.get_file_content(file_id)

            if content:
                exported_docs.append({
                    "file_id": file_id,
                    "name": file_metadata.get("name"),
                    "mime_type": file_metadata.get("mimeType"),
                    "created_time": file_metadata.get("createdTime"),
                    "modified_time": file_metadata.get("modifiedTime"),
                    "size": file_metadata.get("size"),
                    "content_preview": content[:500] if len(content) > 500 else content,
                    "content_length": len(content)
                })

        # Save to file
        with open(output_file, "w") as f:
            json.dump(exported_docs, f, indent=2)

        logger.info(
            "drive_sample_export_complete",
            count=len(exported_docs),
            output_file=output_file
        )

        return exported_docs


if __name__ == "__main__":
    # Test the client
    from dotenv import load_dotenv
    load_dotenv()

    try:
        client = DriveClient()
        if client.test_connection():
            print("✅ Google Drive API connection successful")

            # List files
            files = client.list_files(page_size=5)
            print(f"✅ Retrieved {len(files)} files")

            # Export sample documents
            docs = client.export_sample_documents(num_docs=3)
            print(f"✅ Exported {len(docs)} sample documents")
        else:
            print("❌ Google Drive API connection failed")
    except Exception as e:
        print(f"❌ Error: {e}")
