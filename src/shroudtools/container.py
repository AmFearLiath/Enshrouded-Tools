"""Conservative, read-only signature scanner for Enshrouded KSD files.

This module intentionally does not claim to decode the complete SV2C/S2BH
format. It identifies byte-level observations and candidate block boundaries
for reverse-engineering. Unknown fields and payloads are preserved by offset
rather than interpreted.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import hashlib
import struct

FILE_MAGIC = b"SV2C"
BLOCK_MAGIC = b"S2BH"
ZSTD_MAGIC = b"\x28\xb5\x2f\xfd"


@dataclass(frozen=True)
class BlockCandidate:
    """A candidate block bounded by consecutive S2BH markers."""

    index: int
    offset: int
    end_offset: int
    span_size: int
    header_hex: str
    zstd_frame_offsets: tuple[int, ...]


@dataclass(frozen=True)
class FileInspection:
    """Safe metadata and signature findings; no payload content is exposed."""

    path_name: str
    size_bytes: int
    sha256: str
    magic: str
    has_expected_magic: bool
    block_marker_count: int
    blocks: tuple[BlockCandidate, ...]

    def to_dict(self) -> dict:
        """Return a JSON-serializable representation."""
        result = asdict(self)
        result["blocks"] = [asdict(block) for block in self.blocks]
        return result


def _find_all(data: bytes, needle: bytes) -> list[int]:
    """Return every occurrence of *needle*, including overlapping-safe scans."""
    offsets: list[int] = []
    start = 0
    while True:
        offset = data.find(needle, start)
        if offset < 0:
            return offsets
        offsets.append(offset)
        start = offset + 1


def inspect_bytes(data: bytes, path_name: str = "<memory>") -> FileInspection:
    """Inspect a byte sequence without decompressing or modifying it."""
    block_offsets = _find_all(data, BLOCK_MAGIC)
    blocks: list[BlockCandidate] = []

    for index, offset in enumerate(block_offsets):
        end_offset = block_offsets[index + 1] if index + 1 < len(block_offsets) else len(data)
        # Capture a short header window for local format research. The field
        # meanings are deliberately not decoded at this stage.
        header = data[offset:min(offset + 64, end_offset)]
        zstd_offsets = tuple(
            position - offset
            for position in _find_all(data[offset:end_offset], ZSTD_MAGIC)
        )
        blocks.append(
            BlockCandidate(
                index=index,
                offset=offset,
                end_offset=end_offset,
                span_size=end_offset - offset,
                header_hex=header.hex(),
                zstd_frame_offsets=zstd_offsets,
            )
        )

    return FileInspection(
        path_name=Path(path_name).name,
        size_bytes=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
        magic=data[:4].decode("ascii", errors="replace"),
        has_expected_magic=data.startswith(FILE_MAGIC),
        block_marker_count=len(block_offsets),
        blocks=tuple(blocks),
    )


def inspect_file(path: str | Path) -> FileInspection:
    """Read and inspect a file. The file is never modified."""
    file_path = Path(path)
    data = file_path.read_bytes()
    return inspect_bytes(data, path_name=file_path.name)
