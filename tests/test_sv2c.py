import struct

import pytest

from shroudtools.sv2c import CHUNK_MAGIC, SV2CError, parse_sv2c


def _make_container():
    """Build a minimal synthetic SV2C file with two harmless chunks."""
    chunks = [
        ("alpha", struct.pack("<4sIHI", CHUNK_MAGIC, 2, 0x0002, 1) + b"alpha-payload"),
        ("beta", struct.pack("<4sIHI", CHUNK_MAGIC, 2, 0x0103, 21) + b"beta-payload"),
    ]

    header_size = 0x30
    payload = bytearray(b"\x00" * header_size)
    directory_records = []
    names = bytearray()

    for name, chunk in chunks:
        offset = len(payload)
        payload.extend(chunk)
        directory_records.append((name, offset, len(chunk), 0))

    footer_offset = len(payload)
    payload.extend(b"\x00" * 40)
    directory_start = len(payload)
    payload.extend(b"\x00" * (20 * len(chunks)))
    names_start = len(payload)

    for index, (name, offset, size, checksum) in enumerate(directory_records):
        entry_offset = directory_start + index * 20
        name_bytes = name.encode("ascii")
        rel_name_offset = names_start + len(names) - entry_offset
        struct.pack_into(
            "<IIIII",
            payload,
            entry_offset,
            rel_name_offset,
            len(name_bytes),
            offset,
            size,
            checksum,
        )
        names.extend(name_bytes)

    payload.extend(names)
    payload[:4] = b"SV2C"
    struct.pack_into("<HHI", payload, 4, 2, header_size, len(payload))
    struct.pack_into("<II", payload, 0x28, footer_offset, len(chunks))
    return bytes(payload)


def test_parses_container_directory_and_chunk_headers():
    parsed = parse_sv2c(_make_container())

    assert parsed.info.version == 2
    assert parsed.info.header_size == 0x30
    assert parsed.info.file_size == len(parsed._data)
    assert parsed.info.chunk_count == 2
    assert [chunk.name for chunk in parsed.chunks] == ["alpha", "beta"]
    assert parsed.chunks[0].format_version == 2
    assert parsed.chunks[0].chunk_type == 0x0002
    assert parsed.chunks[0].schema_version == 1
    assert parsed.chunks[1].uses_zstandard is True
    assert parsed.stored_payload("alpha") == b"alpha-payload"


def test_rejects_invalid_magic():
    with pytest.raises(SV2CError, match="SV2C"):
        parse_sv2c(b"NOPE" + b"\x00" * 64)


def test_rejects_header_size_mismatch():
    data = bytearray(_make_container())
    struct.pack_into("<I", data, 8, len(data) + 1)

    with pytest.raises(SV2CError, match="actual size"):
        parse_sv2c(data)


def test_rejects_chunk_with_invalid_signature():
    data = bytearray(_make_container())
    parsed = parse_sv2c(data)
    first = parsed.chunks[0]
    data[first.offset : first.offset + 4] = b"NOPE"

    with pytest.raises(SV2CError, match="S2BH"):
        parse_sv2c(data)
