"""Upload validation for documents (Phase 28).

Validates the size, the content-type against an allow-list, and the
*actual* file bytes' magic-byte signature - never trusting the client-
supplied Content-Type header or filename extension alone (a client can
lie about both). Stdlib only: four known signatures don't need a
dependency like python-magic.
"""

from __future__ import annotations

from app.config import settings


class DocumentValidationError(ValueError):
    """Raised by validate_upload on any failure - the router turns this
    into a 400 with the message as the detail."""


# content_type -> (magic bytes to check at offset 0, file extension used
# for the storage key). Extension is derived from the validated content-
# type, never from the client-supplied filename.
_ALLOWED_CONTENT_TYPES: dict[str, tuple[bytes, str]] = {
    "application/pdf": (b"%PDF-", ".pdf"),
    "image/png": (b"\x89PNG", ".png"),
    "image/jpeg": (b"\xff\xd8\xff", ".jpg"),
}


def allowed_content_types() -> frozenset[str]:
    return frozenset(_ALLOWED_CONTENT_TYPES)


def extension_for_content_type(content_type: str) -> str:
    """Only ever called after validate_upload has already accepted
    `content_type`, so the KeyError path is unreachable in practice."""
    return _ALLOWED_CONTENT_TYPES[content_type][1]


def validate_upload(filename: str, content_type: str, file_bytes: bytes) -> None:
    """Raises DocumentValidationError on any validation failure.

    `filename` is accepted only for a clearer error message - it is never
    used to decide validity (a client can lie about an extension just as
    easily as a Content-Type header)."""
    if not file_bytes:
        raise DocumentValidationError("Uploaded file is empty")

    if len(file_bytes) > settings.document_max_upload_bytes:
        max_mb = settings.document_max_upload_bytes / (1024 * 1024)
        raise DocumentValidationError(f"File exceeds the {max_mb:.0f}MB size limit")

    if content_type not in _ALLOWED_CONTENT_TYPES:
        allowed = ", ".join(sorted(_ALLOWED_CONTENT_TYPES))
        raise DocumentValidationError(
            f"Unsupported content type {content_type!r} for {filename!r}; allowed: {allowed}"
        )

    magic, _ext = _ALLOWED_CONTENT_TYPES[content_type]
    if not file_bytes.startswith(magic):
        raise DocumentValidationError(
            f"File content does not match the claimed content type {content_type!r} "
            f"(magic-byte check failed)"
        )
