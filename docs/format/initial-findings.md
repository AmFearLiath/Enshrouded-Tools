# Initial KSD format observations

**Status:** Preliminary observations; not a complete format specification.  
**Research target:** Local sample named `world0.ksd`.  
**Privacy:** The original sample is not stored in this repository. No world-specific extracted strings or content are reproduced here.

## Direct byte observations

The local world sample measured 5,663,411 bytes and began with:

- ASCII magic: `SV2C`
- A repeated marker: `S2BH`
- 20 occurrences of `S2BH` were found in the sample.
- Zstandard frame magic `28 B5 2F FD` occurred at three offsets in the full file.

The SHA-256 of the private sample is intentionally not published.

## Preliminary container observations

The first four bytes strongly suggest a container-level signature, but the remaining header fields have not yet been mapped.

The `S2BH` marker appears repeatedly. For exploratory inspection, candidate spans were measured from each marker to the next marker (or end of file). This is a useful boundary hypothesis, not proof that each span is a complete independent block.

Some candidate spans contain Zstandard frames. Three frames were successfully decompressed during local analysis using the system Zstandard library:

| Approximate file offset | Compressed frame size | Decompressed size |
|---:|---:|---:|
| 4,830,679 | 354,638 | 1,196,204 |
| 5,185,331 | 233,580 | 807,738 |
| 5,418,976 | 20,625 | 36,816 |

These are observations from one sample. They do not establish the meaning of the corresponding block types.

## What is not established

The following are still unknown:

- Exact SV2C header field definitions.
- Exact S2BH header length and field semantics.
- Whether every S2BH occurrence is a top-level block marker.
- Compression method for all payloads.
- Whether payloads use encryption, checksums, dictionaries, or nested serialization.
- Schemas for world objects, terrain, containers, inventories, NPCs, player state, or circuits.
- Version compatibility and format evolution.

## Research discipline

Every future finding should record:

1. Sample context without publishing private savegame content.
2. File and block offsets.
3. Byte pattern and decoding method.
4. Reproducible test or validation.
5. Confidence: confirmed, likely, or hypothesis.
6. Whether the finding depends on a particular game version.

Do not infer semantic meaning from a readable string alone. A label found in a savegame does not prove the corresponding object structure or location is understood.
