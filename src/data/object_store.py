from __future__ import annotations

import logging
import mimetypes
import os
from datetime import timedelta
from typing import Any

from minio import Minio
from minio.error import S3Error

logger = logging.getLogger(__name__)


class ObjectStore:
    def __init__(
        self,
        endpoint: str = "localhost:9000",
        access_key: str = "minioadmin",
        secret_key: str = "minioadmin",
        bucket: str = "adult-platform",
        secure: bool = False,
    ) -> None:
        self._endpoint = endpoint
        self._access_key = access_key
        self._secret_key = secret_key
        self._bucket = bucket
        self._secure = secure
        self._client: Minio | None = None

    def _get_client(self) -> Minio:
        if self._client is None:
            self._client = Minio(
                self._endpoint,
                access_key=self._access_key,
                secret_key=self._secret_key,
                secure=self._secure,
            )
        return self._client

    def _ensure_bucket(self) -> None:
        client = self._get_client()
        if not client.bucket_exists(self._bucket):
            client.make_bucket(self._bucket)
            logger.info("Created bucket: %s", self._bucket)

    async def upload_file(
        self,
        file_path: str,
        object_name: str | None = None,
        content_type: str | None = None,
        metadata: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        client = self._get_client()
        self._ensure_bucket()

        if object_name is None:
            object_name = os.path.basename(file_path)

        if content_type is None:
            content_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"

        file_size = os.path.getsize(file_path)

        result = client.fput_object(
            bucket_name=self._bucket,
            object_name=object_name,
            file_path=file_path,
            content_type=content_type,
            metadata=metadata or {},
        )

        logger.info("Uploaded %s to %s/%s (%d bytes)", file_path, self._bucket, object_name, file_size)

        return {
            "object_name": object_name,
            "bucket": self._bucket,
            "size": file_size,
            "etag": result.etag,
            "version_id": result.version_id,
        }

    async def upload_data(
        self,
        data: bytes,
        object_name: str,
        content_type: str = "application/octet-stream",
        metadata: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        from io import BytesIO

        client = self._get_client()
        self._ensure_bucket()

        data_stream = BytesIO(data)
        result = client.put_object(
            bucket_name=self._bucket,
            object_name=object_name,
            data=data_stream,
            length=len(data),
            content_type=content_type,
            metadata=metadata or {},
        )

        logger.info("Uploaded data to %s/%s (%d bytes)", self._bucket, object_name, len(data))

        return {
            "object_name": object_name,
            "bucket": self._bucket,
            "size": len(data),
            "etag": result.etag,
        }

    async def download_file(
        self,
        object_name: str,
        file_path: str,
    ) -> dict[str, Any]:
        client = self._get_client()

        stat = client.stat_object(self._bucket, object_name)

        client.fget_object(
            bucket_name=self._bucket,
            object_name=object_name,
            file_path=file_path,
        )

        logger.info("Downloaded %s/%s to %s", self._bucket, object_name, file_path)

        return {
            "object_name": object_name,
            "file_path": file_path,
            "size": stat.size,
            "content_type": stat.content_type,
        }

    async def delete_file(self, object_name: str) -> bool:
        client = self._get_client()

        try:
            client.remove_object(self._bucket, object_name)
            logger.info("Deleted %s/%s", self._bucket, object_name)
            return True
        except S3Error as exc:
            logger.error("Failed to delete %s: %s", object_name, exc)
            return False

    async def list_files(
        self,
        prefix: str = "",
        recursive: bool = True,
    ) -> list[dict[str, Any]]:
        client = self._get_client()

        objects = client.list_objects(
            self._bucket,
            prefix=prefix,
            recursive=recursive,
        )

        files = []
        for obj in objects:
            files.append({
                "object_name": obj.object_name,
                "size": obj.size,
                "last_modified": obj.last_modified.isoformat() if obj.last_modified else None,
                "etag": obj.etag,
                "content_type": obj.content_type,
            })

        return files

    async def get_presigned_url(
        self,
        object_name: str,
        expires: timedelta = timedelta(hours=1),
        method: str = "GET",
    ) -> str:
        client = self._get_client()

        if method == "GET":
            url = client.presigned_get_object(
                self._bucket,
                object_name,
                expires=expires,
            )
        elif method == "PUT":
            url = client.presigned_put_object(
                self._bucket,
                object_name,
                expires=expires,
            )
        else:
            raise ValueError(f"Unsupported method: {method}")

        return url

    async def get_object_stat(self, object_name: str) -> dict[str, Any]:
        client = self._get_client()

        stat = client.stat_object(self._bucket, object_name)

        return {
            "object_name": object_name,
            "size": stat.size,
            "content_type": stat.content_type,
            "last_modified": stat.last_modified.isoformat() if stat.last_modified else None,
            "etag": stat.etag,
            "metadata": stat.metadata,
        }

    async def health_check(self) -> dict[str, Any]:
        try:
            client = self._get_client()
            bucket_exists = client.bucket_exists(self._bucket)
            return {
                "status": "healthy" if bucket_exists else "degraded",
                "bucket": self._bucket,
                "bucket_exists": bucket_exists,
                "endpoint": self._endpoint,
            }
        except Exception as exc:
            return {"status": "unhealthy", "error": str(exc)}
