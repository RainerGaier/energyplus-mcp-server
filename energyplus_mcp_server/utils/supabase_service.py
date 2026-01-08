"""
Supabase Storage Service for EnergyPlus MCP Server

Uploads simulation output files to a Supabase storage bucket.

Usage:
    from energyplus_mcp_server.utils.supabase_service import SupabaseStorageService

    service = SupabaseStorageService()
    result = service.upload_folder(source_folder="/path/to/outputs")
"""

import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


class SupabaseServiceError(Exception):
    """Custom exception for Supabase storage errors"""
    pass


class SupabaseStorageService:
    """Service for uploading simulation files to Supabase storage"""

    def __init__(
        self,
        supabase_url: Optional[str] = None,
        supabase_key: Optional[str] = None,
        bucket_name: Optional[str] = None
    ):
        """
        Initialize the Supabase storage service.

        Args:
            supabase_url: Supabase project URL. If not provided, reads from SUPABASE_URL env var.
            supabase_key: Supabase service key. If not provided, reads from SUPABASE_KEY env var.
            bucket_name: Storage bucket name. If not provided, reads from SUPABASE_BUCKET env var.
        """
        self.supabase_url = supabase_url or os.getenv("SUPABASE_URL")
        self.supabase_key = supabase_key or os.getenv("SUPABASE_KEY")
        self.bucket_name = bucket_name or os.getenv("SUPABASE_BUCKET")

        # Validate configuration
        if not self.supabase_url:
            raise SupabaseServiceError(
                "Supabase URL not configured. "
                "Set SUPABASE_URL environment variable or pass supabase_url parameter."
            )
        if not self.supabase_key:
            raise SupabaseServiceError(
                "Supabase key not configured. "
                "Set SUPABASE_KEY environment variable or pass supabase_key parameter."
            )
        if not self.bucket_name:
            raise SupabaseServiceError(
                "Supabase bucket name not configured. "
                "Set SUPABASE_BUCKET environment variable or pass bucket_name parameter."
            )

        self._client = None

    def _get_client(self):
        """Get or create Supabase client"""
        if self._client is None:
            try:
                from supabase import create_client, Client
            except ImportError:
                raise SupabaseServiceError(
                    "supabase-py not installed. Install with: pip install supabase"
                )

            self._client: Client = create_client(self.supabase_url, self.supabase_key)
            logger.info(f"Connected to Supabase: {self.supabase_url}")

        return self._client

    def _get_mime_type(self, file_path: Path) -> str:
        """Determine MIME type based on file extension"""
        mime_types = {
            ".csv": "text/csv",
            ".html": "text/html",
            ".htm": "text/html",
            ".json": "application/json",
            ".idf": "text/plain",
            ".epw": "text/plain",
            ".sql": "application/x-sqlite3",
            ".obj": "model/obj",
            ".mtl": "text/plain",
            ".glb": "model/gltf-binary",
            ".gltf": "model/gltf+json",
            ".txt": "text/plain",
            ".err": "text/plain",
            ".eso": "text/plain",
            ".eio": "text/plain",
            ".end": "text/plain",
            ".rdd": "text/plain",
            ".mdd": "text/plain",
            ".mtd": "text/plain",
            ".bnd": "text/plain",
            ".shd": "text/plain",
            ".dxf": "application/dxf",
            ".audit": "text/plain",
        }
        return mime_types.get(file_path.suffix.lower(), "application/octet-stream")

    def _delete_folder(self, folder_path: str) -> bool:
        """
        Delete all files in a folder path in the bucket.

        Args:
            folder_path: The folder path in the bucket to delete

        Returns:
            True if deletion was successful or folder didn't exist
        """
        client = self._get_client()

        try:
            # List all files in the folder
            result = client.storage.from_(self.bucket_name).list(folder_path)

            if result and len(result) > 0:
                # Build list of file paths to delete
                files_to_delete = [f"{folder_path}/{item['name']}" for item in result]
                logger.info(f"Deleting {len(files_to_delete)} existing files from {folder_path}")

                # Delete all files
                client.storage.from_(self.bucket_name).remove(files_to_delete)
                logger.info(f"Deleted existing folder contents: {folder_path}")

            return True

        except Exception as e:
            # If folder doesn't exist, that's fine
            logger.debug(f"No existing folder to delete or error: {e}")
            return True

    def upload_file(
        self,
        file_path: str,
        destination_path: str,
        upsert: bool = True
    ) -> Dict[str, Any]:
        """
        Upload a single file to Supabase storage.

        Args:
            file_path: Local path to the file
            destination_path: Path in the bucket (e.g., "folder/filename.csv")
            upsert: If True, overwrite existing file. If False, fail if exists.

        Returns:
            Dict with upload result
        """
        client = self._get_client()
        file_path = Path(file_path)

        if not file_path.exists():
            raise SupabaseServiceError(f"File not found: {file_path}")

        try:
            # Read file content
            with open(file_path, "rb") as f:
                file_content = f.read()

            # Determine content type
            content_type = self._get_mime_type(file_path)

            # Upload to Supabase storage
            result = client.storage.from_(self.bucket_name).upload(
                path=destination_path,
                file=file_content,
                file_options={
                    "content-type": content_type,
                    "upsert": str(upsert).lower()
                }
            )

            logger.info(f"Uploaded: {file_path.name} -> {destination_path}")

            return {
                "success": True,
                "file_name": file_path.name,
                "destination_path": destination_path,
                "size_bytes": len(file_content),
                "content_type": content_type
            }

        except Exception as e:
            logger.error(f"Failed to upload {file_path.name}: {e}")
            raise SupabaseServiceError(f"Upload failed for {file_path.name}: {e}")

    def upload_folder(
        self,
        source_folder: str,
        destination_folder: Optional[str] = None,
        replace_existing: bool = True
    ) -> Dict[str, Any]:
        """
        Upload all files from a folder to Supabase storage.

        Args:
            source_folder: Path to the local folder containing files to upload
            destination_folder: Folder name in the bucket. If not provided, uses source folder name.
            replace_existing: If True, delete existing folder contents before uploading.

        Returns:
            Dict with:
                - success: bool - True if all files uploaded successfully
                - supabase_bucket: str - The bucket name
                - supabase_folder: str - The folder path in the bucket
                - files_uploaded: int - Number of files successfully uploaded
                - files_failed: int - Number of files that failed
                - total_size_bytes: int - Total size of uploaded files
                - files: List of uploaded file details
                - errors: List of any errors encountered
        """
        source_path = Path(source_folder)

        if not source_path.exists():
            raise SupabaseServiceError(f"Source folder not found: {source_folder}")

        if not source_path.is_dir():
            raise SupabaseServiceError(f"Source path is not a directory: {source_folder}")

        # Use source folder name if destination not specified
        folder_name = destination_folder or source_path.name

        # Get list of files to upload
        files_to_upload = [f for f in source_path.iterdir() if f.is_file()]

        if not files_to_upload:
            raise SupabaseServiceError(f"No files found in source folder: {source_folder}")

        logger.info(f"Preparing to upload {len(files_to_upload)} files to {self.bucket_name}/{folder_name}")

        # Delete existing folder contents if requested
        if replace_existing:
            self._delete_folder(folder_name)

        # Upload each file
        uploaded_files: List[Dict[str, Any]] = []
        failed_files: List[Dict[str, Any]] = []
        total_size = 0

        for file_path in files_to_upload:
            destination_path = f"{folder_name}/{file_path.name}"

            try:
                result = self.upload_file(
                    file_path=str(file_path),
                    destination_path=destination_path,
                    upsert=True  # Always upsert individual files
                )
                uploaded_files.append(result)
                total_size += result["size_bytes"]

            except Exception as e:
                error_info = {
                    "file_name": file_path.name,
                    "error": str(e)
                }
                failed_files.append(error_info)
                logger.error(f"Failed to upload {file_path.name}: {e}")

        # Build result
        success = len(failed_files) == 0

        result = {
            "success": success,
            "supabase_bucket": self.bucket_name,
            "supabase_folder": folder_name,
            "files_uploaded": len(uploaded_files),
            "files_failed": len(failed_files),
            "total_size_bytes": total_size,
            "files": uploaded_files
        }

        if failed_files:
            result["errors"] = failed_files

        log_msg = f"Upload complete: {len(uploaded_files)} succeeded, {len(failed_files)} failed"
        if success:
            logger.info(log_msg)
        else:
            logger.warning(log_msg)

        return result

    def list_folder(self, folder_path: str) -> Dict[str, Any]:
        """
        List files in a bucket folder.

        Args:
            folder_path: Path to the folder in the bucket

        Returns:
            Dict with list of files
        """
        client = self._get_client()

        try:
            result = client.storage.from_(self.bucket_name).list(folder_path)

            files = []
            for item in result:
                files.append({
                    "name": item["name"],
                    "path": f"{folder_path}/{item['name']}",
                    "size_bytes": item.get("metadata", {}).get("size"),
                    "last_modified": item.get("updated_at")
                })

            return {
                "success": True,
                "bucket": self.bucket_name,
                "folder": folder_path,
                "file_count": len(files),
                "files": files
            }

        except Exception as e:
            logger.error(f"Failed to list folder {folder_path}: {e}")
            raise SupabaseServiceError(f"Failed to list folder: {e}")

    def get_public_url(self, file_path: str) -> str:
        """
        Get the public URL for a file in the bucket.

        Note: The bucket must be configured as public for this to work.

        Args:
            file_path: Path to the file in the bucket

        Returns:
            Public URL string
        """
        client = self._get_client()
        return client.storage.from_(self.bucket_name).get_public_url(file_path)
