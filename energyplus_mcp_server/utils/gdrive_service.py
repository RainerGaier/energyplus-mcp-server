"""
Google Drive Service for EnergyPlus MCP Server

Provides functionality to upload simulation output folders to Google Drive.

Setup:
    1. Create a Google Cloud project
    2. Enable Google Drive API
    3. Create a service account and download JSON credentials
    4. Set environment variable: GOOGLE_DRIVE_CREDENTIALS=/path/to/credentials.json
    5. Share the destination folder with the service account email

Usage:
    service = GDriveService()
    result = service.upload_folder(source_path, destination_folder_id)
"""

import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

# Google Drive folder URL pattern
# https://drive.google.com/drive/folders/FOLDER_ID
# or https://drive.google.com/drive/u/0/folders/FOLDER_ID


class GDriveServiceError(Exception):
    """Custom exception for Google Drive service errors"""
    pass


class GDriveService:
    """Service for uploading files/folders to Google Drive"""

    def __init__(self, credentials_path: Optional[str] = None):
        """
        Initialize the Google Drive service.

        Args:
            credentials_path: Path to service account JSON credentials.
                            If not provided, uses GOOGLE_DRIVE_CREDENTIALS env var.
        """
        self.credentials_path = credentials_path or os.environ.get("GOOGLE_DRIVE_CREDENTIALS", "")
        self._service = None

    def _get_service(self):
        """Get or create the Google Drive service client."""
        if self._service is not None:
            return self._service

        try:
            from google.oauth2.service_account import Credentials
            from googleapiclient.discovery import build
        except ImportError:
            raise GDriveServiceError(
                "Google Drive dependencies not installed. "
                "Run: pip install google-api-python-client google-auth"
            )

        if not self.credentials_path or not os.path.exists(self.credentials_path):
            raise GDriveServiceError(
                f"Credentials file not found: {self.credentials_path}. "
                "Set GOOGLE_DRIVE_CREDENTIALS environment variable to the path of your service account JSON file."
            )

        try:
            scopes = ["https://www.googleapis.com/auth/drive"]
            creds = Credentials.from_service_account_file(self.credentials_path, scopes=scopes)
            self._service = build("drive", "v3", credentials=creds)
            return self._service
        except Exception as e:
            raise GDriveServiceError(f"Failed to initialize Google Drive service: {str(e)}")

    @staticmethod
    def extract_folder_id(folder_url_or_id: str) -> str:
        """
        Extract folder ID from a Google Drive URL or return as-is if already an ID.

        Args:
            folder_url_or_id: Either a Google Drive folder URL or folder ID

        Returns:
            The folder ID

        Examples:
            - https://drive.google.com/drive/folders/1ABC123xyz -> 1ABC123xyz
            - https://drive.google.com/drive/u/0/folders/1ABC123xyz -> 1ABC123xyz
            - 1ABC123xyz -> 1ABC123xyz
        """
        if "/" not in folder_url_or_id:
            # Already a folder ID
            return folder_url_or_id

        # Extract from URL
        parts = folder_url_or_id.rstrip("/").split("/")
        # Find 'folders' in the path and get the next segment
        for i, part in enumerate(parts):
            if part == "folders" and i + 1 < len(parts):
                # Get the ID, which might have query params
                folder_id = parts[i + 1].split("?")[0]
                return folder_id

        raise GDriveServiceError(f"Could not extract folder ID from: {folder_url_or_id}")

    def create_folder(self, folder_name: str, parent_folder_id: str) -> Dict[str, Any]:
        """
        Create a new folder in Google Drive.

        Args:
            folder_name: Name of the folder to create
            parent_folder_id: ID of the parent folder

        Returns:
            Dict with folder info including 'id' and 'webViewLink'
        """
        service = self._get_service()

        file_metadata = {
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder",
            "parents": [parent_folder_id]
        }

        try:
            folder = service.files().create(
                body=file_metadata,
                fields="id, name, webViewLink"
            ).execute()

            logger.info(f"Created folder: {folder_name} (ID: {folder['id']})")
            return folder

        except Exception as e:
            raise GDriveServiceError(f"Failed to create folder '{folder_name}': {str(e)}")

    def upload_file(self, file_path: Path, parent_folder_id: str) -> Dict[str, Any]:
        """
        Upload a single file to Google Drive.

        Args:
            file_path: Path to the file to upload
            parent_folder_id: ID of the destination folder

        Returns:
            Dict with file info including 'id' and 'name'
        """
        from googleapiclient.http import MediaFileUpload

        service = self._get_service()

        file_metadata = {
            "name": file_path.name,
            "parents": [parent_folder_id]
        }

        # Determine MIME type based on extension
        mime_types = {
            ".csv": "text/csv",
            ".htm": "text/html",
            ".html": "text/html",
            ".idf": "text/plain",
            ".epw": "text/plain",
            ".err": "text/plain",
            ".eso": "text/plain",
            ".eio": "text/plain",
            ".end": "text/plain",
            ".mtd": "text/plain",
            ".mtr": "text/plain",
            ".rdd": "text/plain",
            ".mdd": "text/plain",
            ".shd": "text/plain",
            ".sql": "application/x-sqlite3",
            ".json": "application/json",
            ".txt": "text/plain",
        }

        mime_type = mime_types.get(file_path.suffix.lower(), "application/octet-stream")

        try:
            media = MediaFileUpload(str(file_path), mimetype=mime_type, resumable=True)

            file = service.files().create(
                body=file_metadata,
                media_body=media,
                fields="id, name, size"
            ).execute()

            logger.debug(f"Uploaded file: {file_path.name}")
            return file

        except Exception as e:
            raise GDriveServiceError(f"Failed to upload file '{file_path.name}': {str(e)}")

    def upload_folder(
        self,
        source_folder: str,
        destination_folder_url_or_id: str,
        folder_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Upload an entire folder to Google Drive.

        Args:
            source_folder: Path to the local folder to upload
            destination_folder_url_or_id: Google Drive folder URL or ID
            folder_name: Optional name for the new folder (defaults to source folder name)

        Returns:
            Dict with upload results including:
                - copy_successful: bool
                - folder_created: str (folder name)
                - folder_id: str
                - folder_url: str
                - files_uploaded: int
                - files_failed: int
                - total_size_bytes: int
        """
        source_path = Path(source_folder)

        if not source_path.exists():
            raise GDriveServiceError(f"Source folder not found: {source_folder}")

        if not source_path.is_dir():
            raise GDriveServiceError(f"Source path is not a directory: {source_folder}")

        # Extract destination folder ID
        dest_folder_id = self.extract_folder_id(destination_folder_url_or_id)

        # Determine folder name
        new_folder_name = folder_name or source_path.name

        result = {
            "copy_successful": False,
            "folder_created": new_folder_name,
            "folder_id": None,
            "folder_url": None,
            "files_uploaded": 0,
            "files_failed": 0,
            "failed_files": [],
            "total_size_bytes": 0
        }

        try:
            # Create the destination folder
            new_folder = self.create_folder(new_folder_name, dest_folder_id)
            result["folder_id"] = new_folder["id"]
            result["folder_url"] = new_folder.get("webViewLink", f"https://drive.google.com/drive/folders/{new_folder['id']}")

            # Upload all files in the source folder
            files = list(source_path.iterdir())
            for file_path in files:
                if file_path.is_file():
                    try:
                        uploaded = self.upload_file(file_path, new_folder["id"])
                        result["files_uploaded"] += 1
                        result["total_size_bytes"] += file_path.stat().st_size
                    except Exception as e:
                        logger.error(f"Failed to upload {file_path.name}: {e}")
                        result["files_failed"] += 1
                        result["failed_files"].append(file_path.name)

            # Mark as successful if we uploaded at least one file and had no failures
            result["copy_successful"] = result["files_uploaded"] > 0 and result["files_failed"] == 0

            logger.info(
                f"Upload complete: {result['files_uploaded']} files uploaded, "
                f"{result['files_failed']} failed to folder '{new_folder_name}'"
            )

            return result

        except GDriveServiceError:
            raise
        except Exception as e:
            raise GDriveServiceError(f"Failed to upload folder: {str(e)}")
