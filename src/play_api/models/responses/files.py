"""/files/* contracts (download returns raw bytes — no JSON contract)."""

from __future__ import annotations

from play_api.models.responses.base import Contract, entry


class FileItem(Contract):
    file_id: str
    filename: str
    size: int
    content_type: str
    declared_type: str
    description: str
    download_url: str
    created_at: str
    expires_at: str


class FileUploadResponse(FileItem):
    success: bool
    owner: str  # "user" | "anonymous"


class FileMetadataResponse(FileItem):
    success: bool


class FilesListResponse(Contract):
    success: bool
    total: int
    returned: int
    files: list[FileItem]


CONTRACTS_2XX = (
    entry("POST", r"/files/upload", FileUploadResponse),
    entry("GET", r"/files", FilesListResponse),
    entry("GET", r"/files/[^/]+", FileMetadataResponse),
)
