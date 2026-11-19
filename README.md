# ShroudTools

**Enshrouded Savegame & World Toolkit**

ShroudTools is an independent, modular toolkit for inspecting Enshrouded savegame files and, as the format becomes understood, extracting structured world and character information.

The project begins with a conservative, read-only inspection tool. It does not modify savegames.

## Data privacy

**Original savegames must never be committed to this repository.**

- Do not add `.ksd` files, backups, character data, world data, or extracted private world content.
- Keep real savegames in a local, untracked working directory.
- Use synthetic fixtures for automated tests.
- Review every commit before publishing it.
- Do not publish extracted names, coordinates, inventories, player identifiers, or other world-specific data without explicit approval.

The repository contains source code, format research, documentation, and synthetic tests only.

## Current status

The first research target is the world save `world0.ksd`.

Initial local inspection observed:

- File signature: `SV2C`.
- Repeated block marker: `S2BH`.
- Several Zstandard frame signatures (`28 B5 2F FD`) inside block payloads.
- A mixture of compressed and non-obviously-compressed payloads.

These are observations from one local sample, not a complete specification of the format. Block type meanings and internal schemas remain under investigation.

## Quick start

Requires Python 3.11+.

```bash
python -m pip install -e .
shroudtools inspect /path/to/world0.ksd
```

The inspector reports file metadata, recognized signatures, candidate block boundaries, and Zstandard frame boundaries. It does not print or export savegame payload contents.

## Project structure

```text
src/shroudtools/       Read-only inspection library and CLI
docs/                  Format research and architecture notes
tests/                 Synthetic, non-personal tests
```

## Development principles

1. Preserve original files; all tools are read-only by default.
2. Distinguish confirmed observations from hypotheses.
3. Never silently discard unknown data.
4. Record format/version assumptions and confidence.
5. Add regression tests for every confirmed structure.
6. Keep real savegames out of Git.

## Disclaimer

ShroudTools is an independent community project and is not affiliated with or endorsed by Keen Games.
