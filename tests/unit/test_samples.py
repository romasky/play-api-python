from __future__ import annotations

import struct
import zlib

import pytest

from play_api.utils.samples import BINARY, FILE_LIMIT, WEBHOOK_BODY_LIMIT, sample


def test_limits_are_the_documented_byte_counts() -> None:
    assert FILE_LIMIT == 5_242_880
    assert WEBHOOK_BODY_LIMIT == 65_536
    assert BINARY.startswith(b"\xff\xfe")


def test_tiny_png_is_a_valid_1x1_rgba_png() -> None:
    name, content, content_type = sample("tiny.png")
    assert (name, content_type) == ("tiny.png", "image/png")
    assert content.startswith(b"\x89PNG\r\n\x1a\n")
    chunks, offset = [], 8
    while offset < len(content):
        (length,) = struct.unpack(">I", content[offset : offset + 4])
        kind, data = content[offset + 4 : offset + 8], content[offset + 8 : offset + 8 + length]
        (crc,) = struct.unpack(">I", content[offset + 8 + length : offset + 12 + length])
        assert crc == zlib.crc32(kind + data)
        chunks.append((kind, data))
        offset += 12 + length
    assert [kind for kind, _ in chunks] == [b"IHDR", b"IDAT", b"IEND"]
    assert struct.unpack(">IIBBBBB", chunks[0][1]) == (1, 1, 8, 6, 0, 0, 0)
    assert zlib.decompress(chunks[1][1]) == b"\x00" * 5


@pytest.mark.parametrize(
    ("name", "starts", "content_type"),
    [
        ("tiny.pdf", b"%PDF-1.4\n", "application/pdf"),
        ("note.txt", b"hello from play-api-python\n", "text/plain"),
        ("data.csv", b"id,name\n", "text/csv"),
        ("data.json", b'{"hello":"world"}', "application/json"),
        ("отчёт 1.txt", "отчёт\n".encode(), "text/plain"),
        ("fake.png", b"this is plain text", "image/png"),
        ("program.exe", b"MZ", "application/octet-stream"),
        ("noextension", b"\x00\x01\x02", "application/octet-stream"),
        ("empty.txt", b"", "text/plain"),
    ],
)
def test_named_samples_carry_their_bytes_and_declared_type(name: str, starts: bytes, content_type: str) -> None:
    got_name, content, got_type = sample(name)
    assert (got_name, got_type) == (name, content_type)
    assert content.startswith(starts)


def test_fixed_sizes() -> None:
    assert len(sample("program.exe")[1]) == 64
    assert sample("noextension")[1] == bytes(range(32)) * 4
    assert sample("empty.txt")[1] == b""


@pytest.mark.parametrize(
    ("name", "size"),
    [
        ("exactly-5mib.txt", 5_242_880),
        ("5mib-plus-1.txt", 5_242_881),
        ("5mib-plus-70kib.txt", 5_242_880 + 71_680),
    ],
)
def test_size_boundaries_are_exact(name: str, size: int) -> None:
    got_name, content, content_type = sample(name)
    assert (got_name, content_type, len(content)) == (name, "text/plain", size)
    assert content.strip(b"a") == b""


def test_an_unknown_sample_lists_the_named_and_sized_ones() -> None:
    with pytest.raises(AssertionError, match=r"^unknown sample \(or one of \['5mib-plus-1.txt', .*'tiny.png'"):
        sample("missing.bin")
