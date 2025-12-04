# services/document-service/src/apps/core/services/storage_service.py
"""
Storage Service

MinIO/S3 compatible object storage operations.
Handles file upload, download, presigned URLs, and lifecycle management.
"""

import uuid
import logging
import mimetypes
from typing import BinaryIO, Optional
from datetime import timedelta
from io import BytesIO

import boto3
from botocore.exceptions import ClientError
from django.conf import settings


logger = logging.getLogger(__name__)


class StorageError(Exception):
    """Base exception for storage operations."""
    pass


class FileNotFoundError(StorageError):
    """File not found in storage."""
    pass


class UploadError(StorageError):
    """Error during file upload."""
    pass


class StorageService:
    """
    S3/MinIO storage service for document management.

    Provides:
    - File upload with configurable content types
    - Presigned URL generation for secure access
    - File deletion and copying
    - Bucket management
    - Multipart upload for large files
    """

    def __init__(self):
        self.client = boto3.client(
            's3',
            endpoint_url=settings.AWS_S3_ENDPOINT_URL,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME,
        )
        self.bucket_name = settings.AWS_STORAGE_BUCKET_NAME
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self) -> None:
        """Create bucket if it doesn't exist."""
        try:
            self.client.head_bucket(Bucket=self.bucket_name)
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == '404':
                logger.info(f"Creating bucket: {self.bucket_name}")
                self.client.create_bucket(Bucket=self.bucket_name)
            else:
                logger.error(f"Error checking bucket: {e}")
                raise StorageError(f"Failed to access bucket: {e}")

    # =========================================================================
    # UPLOAD OPERATIONS
    # =========================================================================

    def upload_file(
        self,
        file_content: bytes,
        key: str,
        content_type: str = None,
        metadata: dict = None,
    ) -> dict:
        """
        Upload file content to storage.

        Args:
            file_content: Raw file bytes
            key: Storage path/key
            content_type: MIME type of the file
            metadata: Optional metadata dictionary

        Returns:
            Dict with upload details including ETag
        """
        try:
            extra_args = {}

            if content_type:
                extra_args['ContentType'] = content_type

            if metadata:
                extra_args['Metadata'] = {
                    k: str(v) for k, v in metadata.items()
                }

            # Set default ACL
            extra_args['ACL'] = 'private'

            # Upload
            response = self.client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=file_content,
                **extra_args
            )

            logger.info(f"Uploaded file to {key}, size: {len(file_content)} bytes")

            return {
                'key': key,
                'bucket': self.bucket_name,
                'etag': response.get('ETag', '').strip('"'),
                'size': len(file_content),
                'content_type': content_type,
            }

        except ClientError as e:
            logger.error(f"Upload failed for {key}: {e}")
            raise UploadError(f"Failed to upload file: {e}")

    def upload_fileobj(
        self,
        file_obj: BinaryIO,
        key: str,
        content_type: str = None,
        metadata: dict = None,
    ) -> dict:
        """
        Upload file object to storage.

        Args:
            file_obj: File-like object
            key: Storage path/key
            content_type: MIME type
            metadata: Optional metadata

        Returns:
            Dict with upload details
        """
        try:
            extra_args = {'ACL': 'private'}

            if content_type:
                extra_args['ContentType'] = content_type

            if metadata:
                extra_args['Metadata'] = {
                    k: str(v) for k, v in metadata.items()
                }

            self.client.upload_fileobj(
                file_obj,
                self.bucket_name,
                key,
                ExtraArgs=extra_args
            )

            # Get file size
            file_obj.seek(0, 2)  # Seek to end
            size = file_obj.tell()
            file_obj.seek(0)  # Reset

            logger.info(f"Uploaded file object to {key}")

            return {
                'key': key,
                'bucket': self.bucket_name,
                'size': size,
                'content_type': content_type,
            }

        except ClientError as e:
            logger.error(f"Upload failed for {key}: {e}")
            raise UploadError(f"Failed to upload file: {e}")

    def multipart_upload(
        self,
        file_obj: BinaryIO,
        key: str,
        content_type: str = None,
        chunk_size: int = 10 * 1024 * 1024,  # 10MB chunks
    ) -> dict:
        """
        Upload large file using multipart upload.

        Args:
            file_obj: File-like object
            key: Storage path/key
            content_type: MIME type
            chunk_size: Size of each upload part

        Returns:
            Dict with upload details
        """
        try:
            # Initiate multipart upload
            extra_args = {'ACL': 'private'}
            if content_type:
                extra_args['ContentType'] = content_type

            response = self.client.create_multipart_upload(
                Bucket=self.bucket_name,
                Key=key,
                **extra_args
            )
            upload_id = response['UploadId']

            parts = []
            part_number = 1
            total_size = 0

            try:
                while True:
                    chunk = file_obj.read(chunk_size)
                    if not chunk:
                        break

                    part_response = self.client.upload_part(
                        Bucket=self.bucket_name,
                        Key=key,
                        PartNumber=part_number,
                        UploadId=upload_id,
                        Body=chunk
                    )

                    parts.append({
                        'PartNumber': part_number,
                        'ETag': part_response['ETag']
                    })

                    total_size += len(chunk)
                    part_number += 1

                # Complete the upload
                self.client.complete_multipart_upload(
                    Bucket=self.bucket_name,
                    Key=key,
                    UploadId=upload_id,
                    MultipartUpload={'Parts': parts}
                )

                logger.info(f"Completed multipart upload to {key}, size: {total_size}")

                return {
                    'key': key,
                    'bucket': self.bucket_name,
                    'size': total_size,
                    'content_type': content_type,
                    'parts': len(parts),
                }

            except Exception as e:
                # Abort on failure
                self.client.abort_multipart_upload(
                    Bucket=self.bucket_name,
                    Key=key,
                    UploadId=upload_id
                )
                raise e

        except ClientError as e:
            logger.error(f"Multipart upload failed for {key}: {e}")
            raise UploadError(f"Failed to upload file: {e}")

    # =========================================================================
    # DOWNLOAD OPERATIONS
    # =========================================================================

    def download_file(self, key: str) -> bytes:
        """
        Download file content from storage.

        Args:
            key: Storage path/key

        Returns:
            File content as bytes
        """
        try:
            response = self.client.get_object(
                Bucket=self.bucket_name,
                Key=key
            )
            content = response['Body'].read()
            logger.debug(f"Downloaded file from {key}, size: {len(content)}")
            return content

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == 'NoSuchKey':
                raise FileNotFoundError(f"File not found: {key}")
            logger.error(f"Download failed for {key}: {e}")
            raise StorageError(f"Failed to download file: {e}")

    def download_fileobj(self, key: str, file_obj: BinaryIO) -> None:
        """
        Download file to a file object.

        Args:
            key: Storage path/key
            file_obj: File-like object to write to
        """
        try:
            self.client.download_fileobj(
                self.bucket_name,
                key,
                file_obj
            )
            logger.debug(f"Downloaded file from {key} to file object")

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == 'NoSuchKey':
                raise FileNotFoundError(f"File not found: {key}")
            logger.error(f"Download failed for {key}: {e}")
            raise StorageError(f"Failed to download file: {e}")

    # =========================================================================
    # URL GENERATION
    # =========================================================================

    def get_presigned_url(
        self,
        key: str,
        expires_in: int = 3600,
        response_content_type: str = None,
        response_content_disposition: str = None,
    ) -> str:
        """
        Generate a presigned URL for secure file access.

        Args:
            key: Storage path/key
            expires_in: URL validity in seconds (default 1 hour)
            response_content_type: Override Content-Type header
            response_content_disposition: Override Content-Disposition header

        Returns:
            Presigned URL string
        """
        try:
            params = {
                'Bucket': self.bucket_name,
                'Key': key,
            }

            if response_content_type:
                params['ResponseContentType'] = response_content_type

            if response_content_disposition:
                params['ResponseContentDisposition'] = response_content_disposition

            url = self.client.generate_presigned_url(
                'get_object',
                Params=params,
                ExpiresIn=expires_in
            )

            logger.debug(f"Generated presigned URL for {key}")
            return url

        except ClientError as e:
            logger.error(f"Failed to generate presigned URL for {key}: {e}")
            raise StorageError(f"Failed to generate presigned URL: {e}")

    def get_presigned_upload_url(
        self,
        key: str,
        content_type: str,
        expires_in: int = 3600,
    ) -> dict:
        """
        Generate a presigned URL for direct upload from client.

        Args:
            key: Target storage path/key
            content_type: Expected Content-Type
            expires_in: URL validity in seconds

        Returns:
            Dict with URL and required fields for upload
        """
        try:
            response = self.client.generate_presigned_post(
                self.bucket_name,
                key,
                Fields={'Content-Type': content_type},
                Conditions=[
                    {'Content-Type': content_type},
                    ['content-length-range', 1, 100 * 1024 * 1024],  # Max 100MB
                ],
                ExpiresIn=expires_in
            )

            logger.debug(f"Generated presigned upload URL for {key}")
            return response

        except ClientError as e:
            logger.error(f"Failed to generate presigned upload URL for {key}: {e}")
            raise StorageError(f"Failed to generate presigned upload URL: {e}")

    # =========================================================================
    # FILE MANAGEMENT
    # =========================================================================

    def delete_file(self, key: str) -> bool:
        """
        Delete a file from storage.

        Args:
            key: Storage path/key

        Returns:
            True if deleted successfully
        """
        try:
            self.client.delete_object(
                Bucket=self.bucket_name,
                Key=key
            )
            logger.info(f"Deleted file: {key}")
            return True

        except ClientError as e:
            logger.error(f"Delete failed for {key}: {e}")
            raise StorageError(f"Failed to delete file: {e}")

    def delete_files(self, keys: list[str]) -> dict:
        """
        Delete multiple files from storage.

        Args:
            keys: List of storage keys

        Returns:
            Dict with deleted and error counts
        """
        if not keys:
            return {'deleted': 0, 'errors': 0}

        try:
            objects = [{'Key': key} for key in keys]
            response = self.client.delete_objects(
                Bucket=self.bucket_name,
                Delete={'Objects': objects}
            )

            deleted = len(response.get('Deleted', []))
            errors = len(response.get('Errors', []))

            logger.info(f"Bulk delete: {deleted} deleted, {errors} errors")

            return {'deleted': deleted, 'errors': errors}

        except ClientError as e:
            logger.error(f"Bulk delete failed: {e}")
            raise StorageError(f"Failed to delete files: {e}")

    def copy_file(
        self,
        source_key: str,
        dest_key: str,
        dest_bucket: str = None,
    ) -> dict:
        """
        Copy a file within storage.

        Args:
            source_key: Source storage key
            dest_key: Destination storage key
            dest_bucket: Destination bucket (default: same bucket)

        Returns:
            Dict with copy details
        """
        try:
            dest_bucket = dest_bucket or self.bucket_name
            copy_source = {'Bucket': self.bucket_name, 'Key': source_key}

            response = self.client.copy_object(
                Bucket=dest_bucket,
                Key=dest_key,
                CopySource=copy_source
            )

            logger.info(f"Copied {source_key} to {dest_key}")

            return {
                'source_key': source_key,
                'dest_key': dest_key,
                'dest_bucket': dest_bucket,
                'etag': response.get('CopyObjectResult', {}).get('ETag', ''),
            }

        except ClientError as e:
            logger.error(f"Copy failed from {source_key} to {dest_key}: {e}")
            raise StorageError(f"Failed to copy file: {e}")

    def move_file(self, source_key: str, dest_key: str) -> dict:
        """
        Move a file within storage (copy + delete).

        Args:
            source_key: Source storage key
            dest_key: Destination storage key

        Returns:
            Dict with move details
        """
        result = self.copy_file(source_key, dest_key)
        self.delete_file(source_key)
        logger.info(f"Moved {source_key} to {dest_key}")
        return result

    def file_exists(self, key: str) -> bool:
        """
        Check if a file exists in storage.

        Args:
            key: Storage path/key

        Returns:
            True if file exists
        """
        try:
            self.client.head_object(
                Bucket=self.bucket_name,
                Key=key
            )
            return True
        except ClientError:
            return False

    def get_file_info(self, key: str) -> dict:
        """
        Get file metadata from storage.

        Args:
            key: Storage path/key

        Returns:
            Dict with file info (size, content_type, last_modified, etc.)
        """
        try:
            response = self.client.head_object(
                Bucket=self.bucket_name,
                Key=key
            )

            return {
                'key': key,
                'size': response['ContentLength'],
                'content_type': response.get('ContentType'),
                'last_modified': response['LastModified'],
                'etag': response.get('ETag', '').strip('"'),
                'metadata': response.get('Metadata', {}),
            }

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == '404':
                raise FileNotFoundError(f"File not found: {key}")
            raise StorageError(f"Failed to get file info: {e}")

    # =========================================================================
    # LISTING OPERATIONS
    # =========================================================================

    def list_files(
        self,
        prefix: str = '',
        max_keys: int = 1000,
        continuation_token: str = None,
    ) -> dict:
        """
        List files in storage with optional prefix filter.

        Args:
            prefix: Filter by key prefix
            max_keys: Maximum number of keys to return
            continuation_token: Token for pagination

        Returns:
            Dict with files list and pagination info
        """
        try:
            params = {
                'Bucket': self.bucket_name,
                'MaxKeys': max_keys,
            }

            if prefix:
                params['Prefix'] = prefix

            if continuation_token:
                params['ContinuationToken'] = continuation_token

            response = self.client.list_objects_v2(**params)

            files = []
            for obj in response.get('Contents', []):
                files.append({
                    'key': obj['Key'],
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'],
                    'etag': obj.get('ETag', '').strip('"'),
                })

            return {
                'files': files,
                'count': len(files),
                'is_truncated': response.get('IsTruncated', False),
                'continuation_token': response.get('NextContinuationToken'),
            }

        except ClientError as e:
            logger.error(f"List files failed: {e}")
            raise StorageError(f"Failed to list files: {e}")

    # =========================================================================
    # UTILITY METHODS
    # =========================================================================

    @staticmethod
    def generate_key(
        organization_id: str,
        document_type: str,
        filename: str,
        folder_path: str = None,
    ) -> str:
        """
        Generate a storage key with consistent structure.

        Format: {org_id}/{doc_type}/{optional_folder}/{uuid}_{filename}

        Args:
            organization_id: Organization UUID
            document_type: Document type for categorization
            filename: Original filename
            folder_path: Optional folder path

        Returns:
            Generated storage key
        """
        unique_id = uuid.uuid4().hex[:8]
        safe_filename = filename.replace(' ', '_').replace('/', '_')

        if folder_path:
            return f"{organization_id}/{document_type}/{folder_path}/{unique_id}_{safe_filename}"
        return f"{organization_id}/{document_type}/{unique_id}_{safe_filename}"

    @staticmethod
    def get_content_type(filename: str) -> str:
        """
        Get MIME type for a filename.

        Args:
            filename: File name with extension

        Returns:
            MIME type string
        """
        content_type, _ = mimetypes.guess_type(filename)
        return content_type or 'application/octet-stream'
