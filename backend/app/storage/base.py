from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol


class StorageError(RuntimeError):
    pass


class StorageNotFound(StorageError):
    pass


@dataclass(frozen=True, slots=True)
class StorageObject:
    key: str
    size_bytes: int
    content_type: str
    metadata: dict[str, Any]
    updated_at: datetime


class ObjectStorage(Protocol):
    def put_bytes(
        self,
        *,
        key: str,
        content: bytes,
        content_type: str,
        metadata: dict[str, Any] | None = None,
    ) -> StorageObject:
        ...

    def get_bytes(self, *, key: str) -> bytes:
        ...

    def open_file(self, *, key: str):
        ...

    def delete(self, *, key: str) -> None:
        ...

    def exists(self, *, key: str) -> bool:
        ...

    def list_prefix(self, *, prefix: str) -> list[str]:
        ...

    def read_metadata(self, *, key: str) -> dict[str, Any]:
        ...
