"""
MinIO client for object storage
"""

from typing import Optional, BinaryIO
from io import BytesIO
from minio import Minio
from minio.error import S3Error

from .config import get_settings
from .logging import get_logger

logger = get_logger(__name__)


class MinIOClient:
    """MinIO object storage client"""

    def __init__(
        self,
        endpoint: Optional[str] = None,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        secure: Optional[bool] = None,
    ):
        settings = get_settings()
        self.endpoint = endpoint or settings.minio_endpoint
        self.access_key = access_key or settings.minio_access_key
        self.secret_key = secret_key or settings.minio_secret_key
        self.secure = secure if secure is not None else settings.minio_secure

        self.client = Minio(
            self.endpoint,
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=self.secure,
        )
        logger.info("MinIO client initialized", endpoint=self.endpoint)

    def ensure_bucket(self, bucket_name: str) -> bool:
        """Ensure bucket exists, create if not"""
        try:
            if not self.client.bucket_exists(bucket_name):
                self.client.make_bucket(bucket_name)
                logger.info("Bucket created", bucket=bucket_name)
            return True
        except S3Error as e:
            logger.error("Failed to ensure bucket", bucket=bucket_name, error=str(e))
            return False

    def upload_file(
        self,
        bucket_name: str,
        object_name: str,
        file_data: BinaryIO,
        content_type: str = "application/octet-stream",
        metadata: Optional[dict] = None,
    ) -> bool:
        """Upload a file to MinIO"""
        try:
            self.ensure_bucket(bucket_name)

            # Get file size
            file_data.seek(0, 2)  # Seek to end
            file_size = file_data.tell()
            file_data.seek(0)  # Seek back to start

            self.client.put_object(
                bucket_name,
                object_name,
                file_data,
                length=file_size,
                content_type=content_type,
                metadata=metadata,
            )
            logger.info(
                "File uploaded",
                bucket=bucket_name,
                object=object_name,
                size=file_size,
            )
            return True
        except S3Error as e:
            logger.error(
                "Failed to upload file",
                bucket=bucket_name,
                object=object_name,
                error=str(e),
            )
            return False

    def download_file(self, bucket_name: str, object_name: str) -> Optional[bytes]:
        """Download a file from MinIO"""
        try:
            response = self.client.get_object(bucket_name, object_name)
            data = response.read()
            response.close()
            response.release_conn()
            logger.info("File downloaded", bucket=bucket_name, object=object_name)
            return data
        except S3Error as e:
            logger.error(
                "Failed to download file",
                bucket=bucket_name,
                object=object_name,
                error=str(e),
            )
            return None

    def download_file_stream(
        self, bucket_name: str, object_name: str
    ) -> Optional[BinaryIO]:
        """Download a file as stream from MinIO"""
        try:
            response = self.client.get_object(bucket_name, object_name)
            logger.info(
                "File stream retrieved", bucket=bucket_name, object=object_name
            )
            return response
        except S3Error as e:
            logger.error(
                "Failed to get file stream",
                bucket=bucket_name,
                object=object_name,
                error=str(e),
            )
            return None

    def delete_file(self, bucket_name: str, object_name: str) -> bool:
        """Delete a file from MinIO"""
        try:
            self.client.remove_object(bucket_name, object_name)
            logger.info("File deleted", bucket=bucket_name, object=object_name)
            return True
        except S3Error as e:
            logger.error(
                "Failed to delete file",
                bucket=bucket_name,
                object=object_name,
                error=str(e),
            )
            return False

    def list_files(self, bucket_name: str, prefix: str = "") -> list[str]:
        """List files in a bucket with optional prefix"""
        try:
            objects = self.client.list_objects(bucket_name, prefix=prefix)
            file_names = [obj.object_name for obj in objects]
            logger.info(
                "Files listed", bucket=bucket_name, prefix=prefix, count=len(file_names)
            )
            return file_names
        except S3Error as e:
            logger.error(
                "Failed to list files", bucket=bucket_name, prefix=prefix, error=str(e)
            )
            return []

    def get_file_url(
        self, bucket_name: str, object_name: str, expires: int = 3600
    ) -> Optional[str]:
        """Get presigned URL for file"""
        try:
            url = self.client.presigned_get_object(bucket_name, object_name, expires)
            return url
        except S3Error as e:
            logger.error(
                "Failed to get presigned URL",
                bucket=bucket_name,
                object=object_name,
                error=str(e),
            )
            return None


# Global MinIO client instance
_minio_client: Optional[MinIOClient] = None


def get_minio_client() -> MinIOClient:
    """Get global MinIO client instance"""
    global _minio_client
    if _minio_client is None:
        _minio_client = MinIOClient()
    return _minio_client
