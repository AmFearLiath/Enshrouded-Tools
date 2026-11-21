# SV2C / S2BH container format – initial findings

**Status:** Outer container structure verified against a local world-save sample. Inner world/entity payload schemas remain under investigation.  
**Scope:** Read-only parsing of the .ksd container and chunk directory.  
**Privacy:** Original savegames, world identifiers, extracted world strings, coordinates, inventories, and raw payloads are not stored in this repository.

## 1. Container structure

The inspected format uses the SV2C magic and a 48-byte (0x30) header.

| Offset | Width | Field | Status |
|---:|---:|---|---|
| 0x00 | 4 | Magic SV2C | Confirmed |
| 0x04 | 2 | Container version | Confirmed |
| 0x06 | 2 | Header size | Confirmed |
| 0x08 | 4 | Complete file size | Confirmed |
| 0x0C | 16 | World identifier | Field location confirmed; value is private and must not be published |
| 0x1C | 12 | Additional header data | Not yet interpreted |
| 0x28 | 4 | Directory/footer offset | Confirmed |
| 0x2C | 4 | Directory entry count | Confirmed |

The directory begins at footer_offset + 40. The 40-byte prefix is zero-filled in the inspected sample.

Each directory entry is 20 bytes:

| Relative offset | Width | Field |
|---:|---:|---|
| +0 | 4 | Relative chunk-name offset, relative to the start of this directory entry |
| +4 | 4 | Chunk-name length |
| +8 | 4 | Absolute chunk offset in the file |
| +12 | 4 | Complete chunk size, including its header |
| +16 | 4 | Stored chunk checksum |

The concatenated chunk-name area follows the directory entries. Name offsets must be resolved relative to each individual directory-entry address, not relative to the start of the directory.

## 2. Chunk checksums

The inspected directory checksums match the low 32 bits of XXH3-64 (seed 0), calculated over the complete chunk bytes, including the S2BH header.

Checksum verification is implemented as an optional capability using the xxhash Python package. A missing optional dependency must be reported as “not checked”; it must never be presented as a successful checksum validation.

## 3. S2BH chunk header

A directory entry points to a chunk beginning with a 14-byte header:

| Relative offset | Width | Field |
|---:|---:|---|
| +0 | 4 | Magic S2BH |
| +4 | 4 | Chunk format version |
| +8 | 2 | Chunk type / flags |
| +10 | 4 | Schema version |
| +14 | variable | Stored payload |

The high-byte compression flag identifies Zstandard when bit 0 of the high byte is set. For these chunks, the Zstandard frame begins immediately after the 14-byte header. Other chunk types must not be assumed to use Zstandard.

Unknown chunk types and schema versions must be retained without interpretation.

## 4. Raw signature count is not the directory count

A byte search for S2BH is not a reliable way to count top-level chunks. In the inspected sample, the raw signature count was higher than the number of directory entries. The directory is the authoritative source for top-level chunk boundaries.

The earlier signature-only scanner remains useful as a low-level diagnostic, but its candidate spans must not be treated as actual chunk boundaries.

## 5. Parser implementation

The repository now contains a read-only outer-container parser:

- src/shroudtools/sv2c.py
- tests/test_sv2c.py

It validates the container header, directory bounds, chunk ranges, S2BH signatures, and chunk metadata. When xxhash is installed, it also verifies chunk checksums. Zstandard decompression is optional and guarded by an output-size limit.

CLI entry point:

```bash
pip install -e ".[format,dev]"
shroudtools inspect-container /path/to/world0.ksd
shroudtools inspect-container /path/to/world0.ksd --json
```

The CLI reports metadata only. It does not print chunk payloads or world identifiers.

## 6. Findings from the outer-container pass

The local sample contains directory entries for several distinct chunk families, including metadata, multiple base chunks, an entity_chunk chunk, and supporting data such as logic and custom strings.

The entity_chunk payload can be decompressed successfully. The base chunk family has a different chunk type and must not be passed through the Zstandard path based on size or entropy alone.

These names identify chunk families, not fully understood schemas. In particular, the presence of an entity_chunk does not yet establish how entity records, transforms, object templates, or building pieces are encoded.

## 7. What remains unknown

- The meaning of the additional 12 bytes in the container header.
- The full semantics of each chunk type and schema version.
- The encoding used by the base chunk family.
- The internal schema of entity_chunk and its relationship to base chunks.
- Entity identifiers, template references, component layouts, and transform encoding in the saved payload.
- Whether object placement data is split across multiple chunks.
- Version compatibility and format evolution.

## 8. Next experiments

1. Identify the encoding and framing of the base chunk family without assuming it is Zstandard.
2. Map the decompressed entity_chunk payload structure and locate record boundaries.
3. Identify entity IDs and template references before attempting object classification.
4. Locate transform components and establish coordinate units and axes.
5. Compare controlled before/after saves where one object is placed, moved, or removed.
6. Validate findings against a second independently-created world before promoting sample-specific observations to general format documentation.

A field is considered understood only when its interpretation predicts the result across independent samples or controlled in-game changes.
