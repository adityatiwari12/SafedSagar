"""Storage backend for uploaded document bytes (Phase 28).

`StorageBackend` is a small protocol so a real object-storage backend
(S3/GCS/Azure Blob) can be swapped in later as a one-class change - no
cloud storage credentials exist in this project yet, so
`LocalFilesystemStorage` is the only concrete implementation.

Path-traversal safety: every storage key handed to `save` is a fresh
`uuid4()` (see app.documents.router), never derived from a client-
supplied filename, and `read`/`delete` only ever accept that opaque key -
never a caller-supplied path. `_path_for_key` additionally resolves the
final path and asserts it stays under the storage root, so even a
malformed/unexpected key can't escape the root.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Protocol, runtime_checkable


@runtime_checkable
class StorageBackend(Protocol):
    """Minimal interface every storage backend must implement."""

    def save(self, file_bytes: bytes, key: str) -> None: ...

    def read(self, key: str) -> bytes: ...

    def delete(self, key: str) -> None: ...

    def exists(self, key: str) -> bool: ...


class StorageKeyError(ValueError):
    """Raised when a storage key would resolve outside the storage root."""


class LocalFilesystemStorage:
    """Stores document bytes as plain files under a configurable root
    directory. The key (a uuid4 plus an extension derived from the
    validated content-type - see app.documents.validation) is the entire
    filename; there is no subdirectory structure to traverse into."""

    def __init__(self, root: str | os.PathLike[str]) -> None:
        self._root = Path(root).resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    def _path_for_key(self, key: str) -> Path:
        # Reject any key containing a path separator outright - a valid
        # key is a single filename, never a nested path.
        if not key or "/" in key or "\\" in key or key in (".", ".."):
            raise StorageKeyError(f"invalid storage key: {key!r}")
        candidate = (self._root / key).resolve()
        if candidate.parent != self._root:
            raise StorageKeyError(f"storage key resolves outside storage root: {key!r}")
        return candidate

    def save(self, file_bytes: bytes, key: str) -> None:
        path = self._path_for_key(key)
        path.write_bytes(file_bytes)

    def read(self, key: str) -> bytes:
        path = self._path_for_key(key)
        return path.read_bytes()

    def delete(self, key: str) -> None:
        path = self._path_for_key(key)
        path.unlink(missing_ok=True)

    def exists(self, key: str) -> bool:
        path = self._path_for_key(key)
        return path.is_file()


def get_storage_backend() -> LocalFilesystemStorage:
    """FastAPI-dependency-friendly factory - re-reads settings each call
    (cheap; a Settings instance is already fully constructed) so tests
    that monkeypatch document_storage_root still take effect."""
    from app.config import settings

    return LocalFilesystemStorage(settings.document_storage_root)
