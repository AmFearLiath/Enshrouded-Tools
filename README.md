# ShroudTools

**Enshrouded Savegame & World Toolkit**

ShroudTools is an independent, modular toolkit for inspecting Enshrouded savegame files and, as the format becomes understood, extracting structured world information.

The project begins with conservative, read-only inspection. It does not modify savegames.

## Data privacy

**Original savegames must never be committed to this repository.**

- Do not add .ksd files, backups, character data, world data, or extracted private world content.
- Keep real savegames in a local, untracked working directory.
- Use synthetic fixtures for automated tests.
- Review every commit before publishing it.
- Do not publish extracted names, coordinates, inventories, player identifiers, or other world-specific data without explicit approval.

The repository contains source code, generalized format research, documentation, and synthetic tests only.

## Current status

The outer SV2C container format is now mapped sufficiently for read-only directory parsing:

- 48-byte container header with file size, footer offset, and chunk count.
- 40-byte directory prefix followed by 20-byte chunk entries and a concatenated name area.
- 14-byte S2BH chunk headers.
- XXH3-64 low-32-bit chunk checksums.
- Zstandard compression identified by the chunk type compression flag.

The inner payload schemas are still under investigation. In particular, the entity and base chunk families have not yet been decoded into world objects or transforms.

## Quick start

Requires Python 3.11+.

~~~bash
python -m pip install -e ".[format,dev]"
shroudtools inspect-container /path/to/world0.ksd
shroudtools inspect-container /path/to/world0.ksd --json
~~~

The container inspector reports directory metadata and checksum status. It does not print payload contents or world identifiers. The older signature scanner remains available:

~~~bash
shroudtools inspect /path/to/world0.ksd
~~~

## Project structure

~~~text
src/shroudtools/       Read-only inspection library and CLI
docs/                  Format research and architecture notes
tests/                 Synthetic, non-personal tests
~~~

## Development principles

1. Preserve original files; all tools are read-only by default.
2. Distinguish confirmed observations from hypotheses.
3. Never silently discard unknown data.
4. Record format/version assumptions and confidence.
5. Add regression tests for every confirmed structure.
6. Keep real savegames out of Git.

## Disclaimer

ShroudTools is an independent community project and is not affiliated with or endorsed by Keen Games.
