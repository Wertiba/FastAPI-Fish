"""S3 / MinIO object storage, with a local directory fallback when ``S3_BUCKET`` is empty."""

import asyncio
from collections.abc import AsyncIterator
from datetime import timedelta
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING

from aiobotocore.session import get_session
from botocore.exceptions import BotoCoreError, ClientError
from dishka import Provider, Scope, provide

from app.shared.application.exceptions import ServiceUnavailableError
from app.shared.application.ports.file_storage import FileStorage
from app.shared.infra.config import StorageConfig

if TYPE_CHECKING:  # stubs only, a dev dependency
    from types_aiobotocore_s3 import S3Client


class S3FileStorage(FileStorage):
    def __init__(self, client: "S3Client", bucket: str) -> None:
        self._client = client
        self._bucket = bucket

    async def upload(self, key: str, data: bytes, content_type: str) -> None:
        try:
            await self._client.put_object(Bucket=self._bucket, Key=key, Body=data, ContentType=content_type)
        except (BotoCoreError, ClientError) as exc:
            raise ServiceUnavailableError("Object storage error") from exc

    async def download(self, key: str) -> bytes:
        try:
            response = await self._client.get_object(Bucket=self._bucket, Key=key)
            async with response["Body"] as body:
                return await body.read()
        except self._client.exceptions.NoSuchKey:
            raise FileNotFoundError(key) from None
        except (BotoCoreError, ClientError) as exc:
            raise ServiceUnavailableError("Object storage error") from exc

    async def delete(self, key: str) -> None:
        try:
            await self._client.delete_object(Bucket=self._bucket, Key=key)
        except (BotoCoreError, ClientError) as exc:
            raise ServiceUnavailableError("Object storage error") from exc

    async def download_url(self, key: str, expires_in: timedelta) -> str:
        return await self._client.generate_presigned_url(
            "get_object", Params={"Bucket": self._bucket, "Key": key}, ExpiresIn=int(expires_in.total_seconds())
        )

    async def upload_url(self, key: str, content_type: str, expires_in: timedelta) -> str:
        return await self._client.generate_presigned_url(
            "put_object",
            Params={"Bucket": self._bucket, "Key": key, "ContentType": content_type},
            ExpiresIn=int(expires_in.total_seconds()),
        )


class LocalFileStorage(FileStorage):
    """Development only: files in a local directory; clients cannot get direct URLs."""

    def __init__(self, root: Path) -> None:
        self._root = root.resolve()

    def _path(self, key: str) -> Path:
        relative = PurePosixPath(key)
        if relative.is_absolute() or ".." in relative.parts or not relative.parts:
            raise ValueError(f"Invalid storage key: {key!r}")
        return self._root.joinpath(*relative.parts)

    async def upload(self, key: str, data: bytes, content_type: str) -> None:
        path = self._path(key)

        def write() -> None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)

        await asyncio.to_thread(write)

    async def download(self, key: str) -> bytes:
        return await asyncio.to_thread(self._path(key).read_bytes)

    async def delete(self, key: str) -> None:
        await asyncio.to_thread(self._path(key).unlink, missing_ok=True)

    async def download_url(self, key: str, expires_in: timedelta) -> str:
        raise ServiceUnavailableError("Direct file URLs need S3: set S3_BUCKET")

    async def upload_url(self, key: str, content_type: str, expires_in: timedelta) -> str:
        raise ServiceUnavailableError("Direct file URLs need S3: set S3_BUCKET")


class StorageProvider(Provider):
    scope = Scope.APP

    @provide
    async def storage(self, config: StorageConfig) -> AsyncIterator[FileStorage]:
        if not config.bucket:
            yield LocalFileStorage(Path(config.local_dir))
            return
        session = get_session()
        async with session.create_client(
            "s3",
            endpoint_url=config.endpoint_url,
            region_name=config.region,
            aws_access_key_id=config.access_key,
            aws_secret_access_key=config.secret_key,
        ) as client:
            yield S3FileStorage(client, config.bucket)
