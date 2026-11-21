"""Command-line interface for ShroudTools."""

from __future__ import annotations

import argparse
import json
import sys

from . import __version__
from .container import inspect_file
from .sv2c import SV2CError, parse_sv2c


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="shroudtools",
        description="Read-only Enshrouded savegame inspection toolkit.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect_parser = subparsers.add_parser(
        "inspect",
        help="Scan signatures and candidate block boundaries (legacy scanner).",
    )
    inspect_parser.add_argument("file", help="Path to a local .ksd file.")
    inspect_parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON instead of a human-readable summary.",
    )

    container_parser = subparsers.add_parser(
        "inspect-container",
        help="Parse SV2C directory entries and S2BH chunk headers.",
    )
    container_parser.add_argument("file", help="Path to a local .ksd file.")
    container_parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON instead of a human-readable summary.",
    )
    return parser


def _print_signature_scan(args: argparse.Namespace) -> int:
    try:
        result = inspect_file(args.file)
    except OSError as exc:
        print(f"Could not read input file: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
        return 0

    print(f"File:              {result.path_name}")
    print(f"Size:              {result.size_bytes:,} bytes")
    print(f"Magic:             {result.magic!r}")
    print(f"Expected SV2C:     {'yes' if result.has_expected_magic else 'no'}")
    print(f"S2BH candidates:   {result.block_marker_count}")
    print()
    for block in result.blocks:
        relative_zstd = ", ".join(map(str, block.zstd_frame_offsets)) or "none"
        print(
            f"Block candidate {block.index:02d}: "
            f"0x{block.offset:08X}..0x{block.end_offset:08X} "
            f"({block.span_size:,} bytes); "
            f"Zstd signature offsets relative to candidate: {relative_zstd}"
        )
    print()
    print("Note: candidate boundaries are signature observations, not parsed chunk records.")
    return 0


def _print_container(args: argparse.Namespace) -> int:
    try:
        with open(args.file, "rb") as handle:
            parsed = parse_sv2c(handle.read())
    except OSError as exc:
        print(f"Could not read input file: {exc}", file=sys.stderr)
        return 2
    except SV2CError as exc:
        print(f"Invalid SV2C container: {exc}", file=sys.stderr)
        return 3

    if args.json:
        print(json.dumps(parsed.to_dict(), indent=2))
        return 0

    info = parsed.info
    print(f"Container version: {info.version}")
    print(f"Header size:       {info.header_size} bytes")
    print(f"File size:         {info.file_size:,} bytes")
    print(f"Directory offset:  0x{info.footer_offset:08X}")
    print(f"Chunk count:       {info.chunk_count}")
    print()
    print("Chunks:")
    for chunk in parsed.chunks:
        if chunk.checksum_valid is True:
            checksum = "valid"
        elif chunk.checksum_valid is False:
            checksum = "INVALID"
        else:
            checksum = "not checked (install xxhash)"

        compression = "Zstandard" if chunk.uses_zstandard else "unclassified"
        print(
            f"  {chunk.name:<24} "
            f"offset=0x{chunk.offset:08X} "
            f"size={chunk.size:>9,} "
            f"type=0x{chunk.chunk_type:04X} "
            f"schema={chunk.schema_version:<4} "
            f"{compression:<12} checksum={checksum}"
        )
    print()
    if any(chunk.checksum_valid is False for chunk in parsed.chunks):
        print("WARNING: One or more chunk checksums do not match.")
        return 4
    if all(chunk.checksum_valid is True for chunk in parsed.chunks):
        print("All chunk checksums are valid.")
    else:
        print("Install the optional format dependencies to verify checksums and decompress chunks:")
        print("  pip install 'shroudtools[format]'")
    print("No payload contents were printed or modified.")
    return 0


def main() -> int:
    args = _build_parser().parse_args()
    if args.command == "inspect":
        return _print_signature_scan(args)
    if args.command == "inspect-container":
        return _print_container(args)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
