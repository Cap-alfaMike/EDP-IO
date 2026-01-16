# ============================================================================
# EDP-IO - Storage Provider Abstraction
# ============================================================================
"""
Cloud-agnostic storage interface with implementations for Azure, GCP, and AWS.

SUPPORTED PROVIDERS:
- Azure: ADLS Gen2 (Data Lake Storage)
- GCP: Google Cloud Storage (GCS)
- AWS: Amazon S3

FEATURES:
- Upload/download files and DataFrames
- List objects with prefix filtering
- Delete objects
- Generate signed URLs for temporary access
"""

import os
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, BinaryIO, Dict, List, Optional

from pydantic import BaseModel


class StorageObject(BaseModel):
    """Metadata for a storage object."""

    key: str
    size_bytes: int
    last_modified: datetime
    content_type: Optional[str] = None
    metadata: Dict[str, str] = {}


class StorageProvider(ABC):
    """
    Abstract base class for cloud storage providers.

    All implementations must provide these methods for portability.
    """

    @abstractmethod
    def upload_file(
        self,
        local_path: str,
        remote_path: str,
        container: Optional[str] = None,
    ) -> str:
        """
        Upload a local file to cloud storage.

        Args:
            local_path: Path to local file
            remote_path: Destination path in storage
            container: Bucket/container name (uses default if not specified)

        Returns:
            Full URI of uploaded file (e.g., abfss://..., gs://..., s3://...)
        """
        pass

    @abstractmethod
    def download_file(
        self,
        remote_path: str,
        local_path: str,
        container: Optional[str] = None,
    ) -> str:
        """
        Download a file from cloud storage.

        Returns:
            Path to downloaded local file
        """
        pass

    @abstractmethod
    def upload_bytes(
        self,
        data: bytes,
        remote_path: str,
        container: Optional[str] = None,
        content_type: Optional[str] = None,
    ) -> str:
        """Upload raw bytes to storage."""
        pass

    @abstractmethod
    def download_bytes(
        self,
        remote_path: str,
        container: Optional[str] = None,
    ) -> bytes:
        """Download raw bytes from storage."""
        pass

    @abstractmethod
    def list_objects(
        self,
        prefix: str = "",
        container: Optional[str] = None,
        max_results: int = 1000,
    ) -> List[StorageObject]:
        """List objects with optional prefix filter."""
        pass

    @abstractmethod
    def delete_object(
        self,
        remote_path: str,
        container: Optional[str] = None,
    ) -> bool:
        """Delete an object. Returns True if deleted."""
        pass

    @abstractmethod
    def exists(
        self,
        remote_path: str,
        container: Optional[str] = None,
    ) -> bool:
        """Check if object exists."""
        pass

    @abstractmethod
    def get_uri(
        self,
        remote_path: str,
        container: Optional[str] = None,
    ) -> str:
        """Get the full URI for a path (for Spark access)."""
        pass

    @abstractmethod
    def generate_signed_url(
        self,
        remote_path: str,
        expiration: timedelta = timedelta(hours=1),
        container: Optional[str] = None,
    ) -> str:
        """Generate a temporary signed URL for access."""
        pass


# ============================================================================
# AZURE IMPLEMENTATION
# ============================================================================


class AzureADLSProvider(StorageProvider):
    """
    Azure Data Lake Storage Gen2 implementation.

    Requires:
        - AZURE_STORAGE_ACCOUNT_NAME
        - AZURE_STORAGE_ACCOUNT_KEY or managed identity
    """

    def __init__(
        self,
        account_name: Optional[str] = None,
        default_container: str = "bronze",
    ):
        self.account_name = account_name or os.getenv("AZURE_STORAGE_ACCOUNT_NAME")
        self.default_container = default_container
        self._client = None

    def _get_container(self, container: Optional[str]) -> str:
        return container or self.default_container

    def _get_client(self):
        """Lazy initialization of Azure client."""
        if self._client is None:
            try:
                from azure.identity import DefaultAzureCredential
                from azure.storage.filedatalake import DataLakeServiceClient

                credential = DefaultAzureCredential()
                self._client = DataLakeServiceClient(
                    account_url=f"https://{self.account_name}.dfs.core.windows.net",
                    credential=credential,
                )
            except ImportError:
                raise ImportError("azure-storage-file-datalake not installed")
        return self._client

    def upload_file(
        self, local_path: str, remote_path: str, container: Optional[str] = None
    ) -> str:
        container = self._get_container(container)
        client = self._get_client()

        fs_client = client.get_file_system_client(container)
        file_client = fs_client.get_file_client(remote_path)

        with open(local_path, "rb") as f:
            file_client.upload_data(f, overwrite=True)

        return self.get_uri(remote_path, container)

    def download_file(
        self, remote_path: str, local_path: str, container: Optional[str] = None
    ) -> str:
        container = self._get_container(container)
        client = self._get_client()

        fs_client = client.get_file_system_client(container)
        file_client = fs_client.get_file_client(remote_path)

        Path(local_path).parent.mkdir(parents=True, exist_ok=True)

        with open(local_path, "wb") as f:
            download = file_client.download_file()
            f.write(download.readall())

        return local_path

    def upload_bytes(
        self,
        data: bytes,
        remote_path: str,
        container: Optional[str] = None,
        content_type: Optional[str] = None,
    ) -> str:
        container = self._get_container(container)
        client = self._get_client()

        fs_client = client.get_file_system_client(container)
        file_client = fs_client.get_file_client(remote_path)
        file_client.upload_data(data, overwrite=True)

        return self.get_uri(remote_path, container)

    def download_bytes(self, remote_path: str, container: Optional[str] = None) -> bytes:
        container = self._get_container(container)
        client = self._get_client()

        fs_client = client.get_file_system_client(container)
        file_client = fs_client.get_file_client(remote_path)

        download = file_client.download_file()
        return download.readall()

    def list_objects(
        self, prefix: str = "", container: Optional[str] = None, max_results: int = 1000
    ) -> List[StorageObject]:
        container = self._get_container(container)
        client = self._get_client()

        fs_client = client.get_file_system_client(container)
        paths = fs_client.get_paths(path=prefix)

        objects = []
        for path in paths:
            if not path.is_directory:
                objects.append(
                    StorageObject(
                        key=path.name,
                        size_bytes=path.content_length or 0,
                        last_modified=path.last_modified,
                    )
                )
            if len(objects) >= max_results:
                break

        return objects

    def delete_object(self, remote_path: str, container: Optional[str] = None) -> bool:
        container = self._get_container(container)
        client = self._get_client()

        fs_client = client.get_file_system_client(container)
        file_client = fs_client.get_file_client(remote_path)
        file_client.delete_file()
        return True

    def exists(self, remote_path: str, container: Optional[str] = None) -> bool:
        container = self._get_container(container)
        client = self._get_client()

        fs_client = client.get_file_system_client(container)
        file_client = fs_client.get_file_client(remote_path)
        return file_client.exists()

    def get_uri(self, remote_path: str, container: Optional[str] = None) -> str:
        container = self._get_container(container)
        return f"abfss://{container}@{self.account_name}.dfs.core.windows.net/{remote_path}"

    def generate_signed_url(
        self,
        remote_path: str,
        expiration: timedelta = timedelta(hours=1),
        container: Optional[str] = None,
    ) -> str:
        # Implementation would use SAS tokens
        container = self._get_container(container)
        return (
            f"https://{self.account_name}.blob.core.windows.net/{container}/{remote_path}?sas=..."
        )


# ============================================================================
# GCP IMPLEMENTATION
# ============================================================================


class GCPGCSProvider(StorageProvider):
    """
    Google Cloud Storage implementation.

    Requires:
        - GOOGLE_CLOUD_PROJECT
        - GOOGLE_APPLICATION_CREDENTIALS or workload identity
    """

    def __init__(
        self,
        project_id: Optional[str] = None,
        default_bucket: str = "edp-io-bronze",
    ):
        self.project_id = project_id or os.getenv("GOOGLE_CLOUD_PROJECT")
        self.default_bucket = default_bucket
        self._client = None

    def _get_bucket(self, container: Optional[str]) -> str:
        return container or self.default_bucket

    def _get_client(self):
        if self._client is None:
            try:
                from google.cloud import storage

                self._client = storage.Client(project=self.project_id)
            except ImportError:
                raise ImportError("google-cloud-storage not installed")
        return self._client

    def upload_file(
        self, local_path: str, remote_path: str, container: Optional[str] = None
    ) -> str:
        bucket_name = self._get_bucket(container)
        client = self._get_client()

        bucket = client.bucket(bucket_name)
        blob = bucket.blob(remote_path)
        blob.upload_from_filename(local_path)

        return self.get_uri(remote_path, bucket_name)

    def download_file(
        self, remote_path: str, local_path: str, container: Optional[str] = None
    ) -> str:
        bucket_name = self._get_bucket(container)
        client = self._get_client()

        bucket = client.bucket(bucket_name)
        blob = bucket.blob(remote_path)

        Path(local_path).parent.mkdir(parents=True, exist_ok=True)
        blob.download_to_filename(local_path)

        return local_path

    def upload_bytes(
        self,
        data: bytes,
        remote_path: str,
        container: Optional[str] = None,
        content_type: Optional[str] = None,
    ) -> str:
        bucket_name = self._get_bucket(container)
        client = self._get_client()

        bucket = client.bucket(bucket_name)
        blob = bucket.blob(remote_path)
        blob.upload_from_string(data, content_type=content_type)

        return self.get_uri(remote_path, bucket_name)

    def download_bytes(self, remote_path: str, container: Optional[str] = None) -> bytes:
        bucket_name = self._get_bucket(container)
        client = self._get_client()

        bucket = client.bucket(bucket_name)
        blob = bucket.blob(remote_path)
        return blob.download_as_bytes()

    def list_objects(
        self, prefix: str = "", container: Optional[str] = None, max_results: int = 1000
    ) -> List[StorageObject]:
        bucket_name = self._get_bucket(container)
        client = self._get_client()

        bucket = client.bucket(bucket_name)
        blobs = bucket.list_blobs(prefix=prefix, max_results=max_results)

        return [
            StorageObject(
                key=blob.name,
                size_bytes=blob.size or 0,
                last_modified=blob.updated,
                content_type=blob.content_type,
            )
            for blob in blobs
        ]

    def delete_object(self, remote_path: str, container: Optional[str] = None) -> bool:
        bucket_name = self._get_bucket(container)
        client = self._get_client()

        bucket = client.bucket(bucket_name)
        blob = bucket.blob(remote_path)
        blob.delete()
        return True

    def exists(self, remote_path: str, container: Optional[str] = None) -> bool:
        bucket_name = self._get_bucket(container)
        client = self._get_client()

        bucket = client.bucket(bucket_name)
        blob = bucket.blob(remote_path)
        return blob.exists()

    def get_uri(self, remote_path: str, container: Optional[str] = None) -> str:
        bucket_name = self._get_bucket(container)
        return f"gs://{bucket_name}/{remote_path}"

    def generate_signed_url(
        self,
        remote_path: str,
        expiration: timedelta = timedelta(hours=1),
        container: Optional[str] = None,
    ) -> str:
        bucket_name = self._get_bucket(container)
        client = self._get_client()

        bucket = client.bucket(bucket_name)
        blob = bucket.blob(remote_path)
        return blob.generate_signed_url(expiration=expiration)


# ============================================================================
# AWS IMPLEMENTATION
# ============================================================================


class AWSS3Provider(StorageProvider):
    """
    Amazon S3 implementation.

    Requires:
        - AWS_ACCESS_KEY_ID + AWS_SECRET_ACCESS_KEY or IAM role
    """

    def __init__(
        self,
        region: str = "us-east-1",
        default_bucket: str = "edp-io-bronze",
    ):
        self.region = region
        self.default_bucket = default_bucket
        self._client = None

    def _get_bucket(self, container: Optional[str]) -> str:
        return container or self.default_bucket

    def _get_client(self):
        if self._client is None:
            try:
                import boto3

                self._client = boto3.client("s3", region_name=self.region)
            except ImportError:
                raise ImportError("boto3 not installed")
        return self._client

    def upload_file(
        self, local_path: str, remote_path: str, container: Optional[str] = None
    ) -> str:
        bucket = self._get_bucket(container)
        client = self._get_client()

        client.upload_file(local_path, bucket, remote_path)
        return self.get_uri(remote_path, bucket)

    def download_file(
        self, remote_path: str, local_path: str, container: Optional[str] = None
    ) -> str:
        bucket = self._get_bucket(container)
        client = self._get_client()

        Path(local_path).parent.mkdir(parents=True, exist_ok=True)
        client.download_file(bucket, remote_path, local_path)
        return local_path

    def upload_bytes(
        self,
        data: bytes,
        remote_path: str,
        container: Optional[str] = None,
        content_type: Optional[str] = None,
    ) -> str:
        bucket = self._get_bucket(container)
        client = self._get_client()

        extra_args = {"ContentType": content_type} if content_type else {}
        client.put_object(Bucket=bucket, Key=remote_path, Body=data, **extra_args)
        return self.get_uri(remote_path, bucket)

    def download_bytes(self, remote_path: str, container: Optional[str] = None) -> bytes:
        bucket = self._get_bucket(container)
        client = self._get_client()

        response = client.get_object(Bucket=bucket, Key=remote_path)
        return response["Body"].read()

    def list_objects(
        self, prefix: str = "", container: Optional[str] = None, max_results: int = 1000
    ) -> List[StorageObject]:
        bucket = self._get_bucket(container)
        client = self._get_client()

        response = client.list_objects_v2(Bucket=bucket, Prefix=prefix, MaxKeys=max_results)

        return [
            StorageObject(
                key=obj["Key"],
                size_bytes=obj["Size"],
                last_modified=obj["LastModified"],
            )
            for obj in response.get("Contents", [])
        ]

    def delete_object(self, remote_path: str, container: Optional[str] = None) -> bool:
        bucket = self._get_bucket(container)
        client = self._get_client()

        client.delete_object(Bucket=bucket, Key=remote_path)
        return True

    def exists(self, remote_path: str, container: Optional[str] = None) -> bool:
        bucket = self._get_bucket(container)
        client = self._get_client()

        try:
            client.head_object(Bucket=bucket, Key=remote_path)
            return True
        except:
            return False

    def get_uri(self, remote_path: str, container: Optional[str] = None) -> str:
        bucket = self._get_bucket(container)
        return f"s3://{bucket}/{remote_path}"

    def generate_signed_url(
        self,
        remote_path: str,
        expiration: timedelta = timedelta(hours=1),
        container: Optional[str] = None,
    ) -> str:
        bucket = self._get_bucket(container)
        client = self._get_client()

        return client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": remote_path},
            ExpiresIn=int(expiration.total_seconds()),
        )


# ============================================================================
# MOCK IMPLEMENTATION
# ============================================================================


class MockStorageProvider(StorageProvider):
    """Mock storage for development and testing."""

    def __init__(self, base_path: str = "./data"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _get_path(self, remote_path: str, container: Optional[str]) -> Path:
        container = container or "default"
        return self.base_path / container / remote_path

    def upload_file(
        self, local_path: str, remote_path: str, container: Optional[str] = None
    ) -> str:
        dest = self._get_path(remote_path, container)
        dest.parent.mkdir(parents=True, exist_ok=True)

        import shutil

        shutil.copy2(local_path, dest)
        return f"file://{dest.absolute()}"

    def download_file(
        self, remote_path: str, local_path: str, container: Optional[str] = None
    ) -> str:
        src = self._get_path(remote_path, container)
        Path(local_path).parent.mkdir(parents=True, exist_ok=True)

        import shutil

        shutil.copy2(src, local_path)
        return local_path

    def upload_bytes(
        self,
        data: bytes,
        remote_path: str,
        container: Optional[str] = None,
        content_type: Optional[str] = None,
    ) -> str:
        dest = self._get_path(remote_path, container)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        return f"file://{dest.absolute()}"

    def download_bytes(self, remote_path: str, container: Optional[str] = None) -> bytes:
        return self._get_path(remote_path, container).read_bytes()

    def list_objects(
        self, prefix: str = "", container: Optional[str] = None, max_results: int = 1000
    ) -> List[StorageObject]:
        base = self._get_path("", container)
        if not base.exists():
            return []

        objects = []
        for path in base.rglob(f"{prefix}*"):
            if path.is_file():
                stat = path.stat()
                objects.append(
                    StorageObject(
                        key=str(path.relative_to(base)),
                        size_bytes=stat.st_size,
                        last_modified=datetime.fromtimestamp(stat.st_mtime),
                    )
                )
        return objects[:max_results]

    def delete_object(self, remote_path: str, container: Optional[str] = None) -> bool:
        path = self._get_path(remote_path, container)
        if path.exists():
            path.unlink()
            return True
        return False

    def exists(self, remote_path: str, container: Optional[str] = None) -> bool:
        return self._get_path(remote_path, container).exists()

    def get_uri(self, remote_path: str, container: Optional[str] = None) -> str:
        return f"file://{self._get_path(remote_path, container).absolute()}"

    def generate_signed_url(
        self,
        remote_path: str,
        expiration: timedelta = timedelta(hours=1),
        container: Optional[str] = None,
    ) -> str:
        return self.get_uri(remote_path, container)


# ============================================================================
# FACTORY
# ============================================================================


def get_storage_provider(provider: Optional[str] = None) -> StorageProvider:
    """
    Factory function to get the configured storage provider.

    Args:
        provider: Override provider (azure, gcp, aws, mock)

    Returns:
        Configured StorageProvider instance
    """
    provider = provider or os.getenv("CLOUD_PROVIDER", "mock")

    if provider == "azure":
        return AzureADLSProvider()
    elif provider == "gcp":
        return GCPGCSProvider()
    elif provider == "aws":
        return AWSS3Provider()
    else:
        return MockStorageProvider()
