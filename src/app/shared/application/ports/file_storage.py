from datetime import timedelta
from typing import Protocol


class FileStorage(Protocol):
    """Object storage (S3 / MinIO). Keys are opaque paths such as ``pets/<id>/avatar.jpg``."""

    async def upload(self, key: str, data: bytes, content_type: str) -> None: ...

    async def download(self, key: str) -> bytes:
        """Raises ``FileNotFoundError`` for an unknown key."""
        ...

    async def delete(self, key: str) -> None:
        """Deleting an unknown key is not an error."""
        ...

    async def download_url(self, key: str, expires_in: timedelta) -> str:
        """A temporary URL the client (browser, mobile app) downloads from directly."""
        ...

    async def upload_url(self, key: str, content_type: str, expires_in: timedelta) -> str:
        """A temporary URL the client uploads to with ``PUT``, so large files bypass the API."""
        ...
