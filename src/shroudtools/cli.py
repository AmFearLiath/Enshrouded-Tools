"""Command-line interface for ShroudTools."""

from __future__ import annotations

import argparse
import json
import sys

from . import __version__
from .container import inspect_file


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="shroudtools",
        description="Read-only Enshrouded savegame inspection toolkit.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect_parser = subparsers.add_parser(
        "inspect",
        help="Inspect container signatures and candidate block boundaries.",
    )
    inspect_parser.add_argument("file", help="Path to a local .ksd file.")
    inspect_parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON instead of a human-readable summary.",
    )
    return parser


def main() -> int:
    args = _build_parser().parse_args()

    if args.command == "inspect":
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
        print("Note: block boundaries and header fields are observations, not a decoded format.")
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
