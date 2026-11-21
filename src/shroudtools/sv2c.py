"""Read-only parser for the Enshrouded SV2C container format.

This module parses the outer container and S2BH chunk headers only. It does
not interpret entity, building, terrain, or game-specific payload schemas.
Unknown chunks are retained as byte ranges and are never discarded.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from io import BytesIO
from typing import Any

FILE_MAGIC = b"SV2C"
CHUNK_MAGIC = b"S2BH"
CONTAINER_HEADER_SIZE = 0x30
CHUNK_HEADER_SIZE = 14
DIRECTORY_PADDING_SIZE = 40
DIRECTORY_ENTRY_SIZE = 20
MAX_CHUNK_COUNT = 100_000
DEFAULT_MAX_DECOMPRESSED_SIZE = 64 * 1024 * 1024


class SV2CError(ValueError):
    """Raised when an SV2C container is malformed or inconsistent."""


@dataclass(frozen=True)
class ChunkEntry:
    """Directory metadata and the decoded S2BH header for one chunk."""

    index: int
    name: str
    offset: int
    size: int
    checksum: int
    format_version: int
    chunk_type: int
    schema_version: int
    checksum_valid: bool | None

    @property
    def payload_offset(self) -> int:
        """Absolute file offset of the chunk payload, after its 14-byte header."""
        return self.offset + CHUNK_HEADER_SIZE

    @property
    def payload_size(self) -> int:
        """Stored payload size, excluding the S2BH header."""
        return self.size - CHUNK_HEADER_SIZE

    @property
    def uses_zstandard(self) -> bool:
        """Whether the high-byte compression flag identifies a Zstandard chunk."""
        return ((self.chunk_type >> 8) & 1) == 1


@dataclass(frozen=True)
class ContainerInfo:
    """Public, non-identity container metadata."""

    version: int
    header_size: int
    file_size: int
    footer_offset: int
    chunk_count: int


@dataclass(frozen=True)
class ParsedContainer:
    """Parsed container metadata plus the original immutable byte sequence."""

    info: ContainerInfo
    chunks: tuple[ChunkEntry, ...]
    _data: bytes

    def get_chunk(self, name: str) -> ChunkEntry:
        """Return a chunk by its exact directory name."""
        for chunk in self.chunks:
            if chunk.name == name:
                return chunk
        raise KeyError(f"Chunk not found: {name}")

    def chunk_bytes(self, chunk: ChunkEntry | str) -> bytes:
        """Return the complete S2BH chunk, including its header."""
        entry = self.get_chunk(chunk) if isinstance(chunk, str) else chunk
        return self._data[entry.offset : entry.offset + entry.size]

    def stored_payload(self, chunk: ChunkEntry | str) -> bytes:
        """Return the stored payload without attempting decompression."""
        entry = self.get_chunk(chunk) if isinstance(chunk, str) else chunk
        return self._data[entry.payload_offset : entry.offset + entry.size]

    def decompress_payload(
        self,
        chunk: ChunkEntry | str,
        *,
        max_output_size: int = DEFAULT_MAX_DECOMPRESSED_SIZE,
    ) -> bytes:
        """Decompress a Zstandard payload with a hard output-size limit.

        Requires the optional 'zstandard' package. Non-Zstandard chunks are
        rejected rather than being guessed or silently passed through.
        """
        entry = self.get_chunk(chunk) if isinstance(chunk, str) else chunk
        if not entry.uses_zstandard:
            raise SV2CError(f"Chunk {entry.name!r} is not marked as Zstandard-compressed.")
        if max_output_size <= 0:
            raise ValueError("max_output_size must be greater than zero.")

        try:
            import zstandard
        except ImportError as exc:
            raise SV2CError(
                "Zstandard support is optional. Install it with: "
                "pip install 'shroudtools[zstd]'"
            ) from exc

        source = BytesIO(self.stored_payload(entry))
        output = bytearray()
        try:
            with zstandard.ZstdDecompressor().stream_reader(source) as reader:
                while True:
                    remaining = max_output_size + 1 - len(output)
                    if remaining <= 0:
                        raise SV2CError(
                            f"Decompressed chunk {entry.name!r} exceeds "
                            f"the {max_output_size:,}-byte safety limit."
                        )
                    part = reader.read(min(1024 * 1024, remaining))
                    if not part:
                        break
                    output.extend(part)
        except SV2CError:
            raise
        except zstandard.ZstdError as exc:
            raise SV2CError(f"Could not decompress chunk {entry.name!r}: {exc}") from exc

        if len(output) > max_output_size:
            raise SV2CError(
                f"Decompressed chunk {entry.name!r} exceeds "
                f"the {max_output_size:,}-byte safety limit."
            )
        return bytes(output)

    def to_dict(self) -> dict[str, Any]:
        """Return safe JSON metadata; no payload bytes or world identifiers."""
        return {
            "container": asdict(self.info),
            "chunks": [
                {
                    **asdict(chunk),
                    "uses_zstandard": chunk.uses_zstandard,
                    "payload_size": chunk.payload_size,
                }
                for chunk in self.chunks
            ],
        }


def _read_ascii_name(data: bytes, start: int, length: int, index: int) -> str:
    raw = data[start : start + length]
    if not raw:
        return f"unnamed_{index:03d}"
    if all(0x20 <= byte <= 0x7E for byte in raw):
        return raw.decode("ascii")
    # Avoid leaking or misrepresenting arbitrary binary name bytes.
    return f"unnamed_{index:03d}_{raw[:8].hex()}"


def _optional_xxh3_low32(data: bytes) -> int | None:
    """Return low 32 bits of XXH3-64, or None when xxhash is not installed."""
    try:
        import xxhash
    except ImportError:
        return None
    return xxhash.xxh3_64_intdigest(data) & 0xFFFFFFFF


def parse_sv2c(data: bytes | bytearray | memoryview) -> ParsedContainer:
    """Parse and validate an SV2C container without changing the input.

    The parser validates container bounds, directory entries, S2BH headers,
    and (when the optional xxhash package is installed) chunk checksums.
    Unknown chunk types and schemas are accepted and preserved.
    """
    raw = bytes(data)
    if len(raw) < CONTAINER_HEADER_SIZE:
        raise SV2CError("File is too small to contain an SV2C header.")
    if raw[:4] != FILE_MAGIC:
        raise SV2CError('Missing "SV2C" container signature.')

    version = int.from_bytes(raw[4:6], "little")
    header_size = int.from_bytes(raw[6:8], "little")
    file_size = int.from_bytes(raw[8:12], "little")
    footer_offset = int.from_bytes(raw[0x28:0x2C], "little")
    chunk_count = int.from_bytes(raw[0x2C:0x30], "little")

    if header_size < CONTAINER_HEADER_SIZE:
        raise SV2CError(f"Invalid header size: {header_size}.")
    if file_size != len(raw):
        raise SV2CError(
            f"Header file size ({file_size}) does not match actual size ({len(raw)})."
        )
    if chunk_count > MAX_CHUNK_COUNT:
        raise SV2CError(f"Unreasonable chunk count: {chunk_count}.")
    if footer_offset < header_size or footer_offset > len(raw):
        raise SV2CError(f"Invalid directory/footer offset: {footer_offset}.")

    directory_start = footer_offset + DIRECTORY_PADDING_SIZE
    directory_end = directory_start + chunk_count * DIRECTORY_ENTRY_SIZE
    if directory_end > len(raw):
        raise SV2CError("Chunk directory extends beyond the end of the file.")

    info = ContainerInfo(
        version=version,
        header_size=header_size,
        file_size=file_size,
        footer_offset=footer_offset,
        chunk_count=chunk_count,
    )

    chunks: list[ChunkEntry] = []
    ranges: list[tuple[int, int, str]] = []

    for index in range(chunk_count):
        entry_offset = directory_start + index * DIRECTORY_ENTRY_SIZE
        rel_name_offset = int.from_bytes(raw[entry_offset : entry_offset + 4], "little")
        name_length = int.from_bytes(raw[entry_offset + 4 : entry_offset + 8], "little")
        chunk_offset = int.from_bytes(raw[entry_offset + 8 : entry_offset + 12], "little")
        chunk_size = int.from_bytes(raw[entry_offset + 12 : entry_offset + 16], "little")
        expected_checksum = int.from_bytes(raw[entry_offset + 16 : entry_offset + 20], "little")

        name_start = entry_offset + rel_name_offset
        if name_length == 0 or name_start < directory_end or name_start + name_length > len(raw):
            raise SV2CError(f"Invalid name range in directory entry {index}.")
        name = _read_ascii_name(raw, name_start, name_length, index)

        chunk_end = chunk_offset + chunk_size
        if chunk_offset < header_size or chunk_size < CHUNK_HEADER_SIZE or chunk_end > footer_offset:
            raise SV2CError(f"Invalid data range for chunk {name!r}.")
        if raw[chunk_offset : chunk_offset + 4] != CHUNK_MAGIC:
            raise SV2CError(f"Chunk {name!r} is missing its S2BH signature.")

        format_version = int.from_bytes(raw[chunk_offset + 4 : chunk_offset + 8], "little")
        chunk_type = int.from_bytes(raw[chunk_offset + 8 : chunk_offset + 10], "little")
        schema_version = int.from_bytes(raw[chunk_offset + 10 : chunk_offset + 14], "little")

        complete_chunk = raw[chunk_offset:chunk_end]
        actual_checksum = _optional_xxh3_low32(complete_chunk)
        checksum_valid = (
            None if actual_checksum is None else actual_checksum == expected_checksum
        )

        chunks.append(
            ChunkEntry(
                index=index,
                name=name,
                offset=chunk_offset,
                size=chunk_size,
                checksum=expected_checksum,
                format_version=format_version,
                chunk_type=chunk_type,
                schema_version=schema_version,
                checksum_valid=checksum_valid,
            )
        )
        ranges.append((chunk_offset, chunk_end, name))

    # A chunk directory must not point multiple entries at overlapping payload ranges.
    ranges.sort()
    for previous, current in zip(ranges, ranges[1:]):
        if current[0] < previous[1]:
            raise SV2CError(
                f"Chunk ranges overlap: {previous[2]!r} and {current[2]!r}."
            )

    return ParsedContainer(info=info, chunks=tuple(chunks), _data=raw)
