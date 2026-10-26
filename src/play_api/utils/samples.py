"""In-memory test files for /files/upload — no binary fixtures in the repo.

`sample(name)` → (filename, bytes, declared content type). Sizes are exact so boundary scenarios can
assert them: the upload part limit is 5 MiB (5 242 880 bytes) and the whole multipart body may exceed
that by at most 64 KiB.
"""

from __future__ import annotations

import zlib

from play_api.utils.lookup import choose

FILE_LIMIT = 5 * 1024 * 1024
WEBHOOK_BODY_LIMIT = 64 * 1024


def _png_1x1() -> bytes:
    def chunk(kind: bytes, data: bytes) -> bytes:
        return len(data).to_bytes(4, "big") + kind + data + zlib.crc32(kind + data).to_bytes(4, "big")

    ihdr = (1).to_bytes(4, "big") * 2 + bytes([8, 6, 0, 0, 0])  # 1×1, 8-bit RGBA
    idat = zlib.compress(b"\x00\x00\x00\x00\x00")  # filter byte + one transparent pixel
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")


_PDF = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Count 0/Kids[]>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF\n"  # noqa: E501
BINARY = b"\xff\xfe\x00\x01binary"

_SAMPLES: dict[str, tuple[bytes, str]] = {
    "tiny.png": (_png_1x1(), "image/png"),
    "tiny.pdf": (_PDF, "application/pdf"),
    "note.txt": (b"hello from play-api-python\n", "text/plain"),
    "data.csv": (b"id,name\n1,alice\n", "text/csv"),
    "data.json": (b'{"hello":"world"}', "application/json"),
    "отчёт 1.txt": ("отчёт\n".encode(), "text/plain"),
    "fake.png": (b"this is plain text pretending to be a PNG", "image/png"),
    "program.exe": (b"MZ\x90\x00\x03\x00\x00\x00" + bytes(56), "application/octet-stream"),
    # NUL-leading bytes: Go's sniffer reads a leading ff fe as a UTF-16 BOM (→ text/plain), not binary
    "noextension": (bytes(range(32)) * 4, "application/octet-stream"),
    "empty.txt": (b"", "text/plain"),
}
# size boundaries, built on demand (≈ 5 MiB each)
_SIZED: dict[str, int] = {
    "exactly-5mib.txt": FILE_LIMIT,
    "5mib-plus-1.txt": FILE_LIMIT + 1,
    "5mib-plus-70kib.txt": FILE_LIMIT + 70 * 1024,
}


def sample(name: str) -> tuple[str, bytes, str]:
    if name in _SIZED:
        return name, b"a" * _SIZED[name], "text/plain"
    content, content_type = choose(_SAMPLES, name, f"sample (or one of {sorted(_SIZED)})")
    return name, content, content_type
