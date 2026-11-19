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


## Additional structural observation

A closer comparison of the repeated block markers shows that the bytes following `S2BH` are not safely interpretable as one universal fixed header yet.

Across the inspected sample:

- The next four bytes repeatedly contain the same little-endian value.
- The following bytes vary and appear to contain at least two small integer-like fields in several block families.
- Some block families place a Zstandard frame immediately after a short preamble.
- Other block families contain additional integer-like fields or opaque binary data before any recognizable payload.
- Small metadata-like blocks and large data-heavy blocks coexist.

This is enough to justify a typed block-reader architecture, but not enough to assign semantic names to the fields. In particular, the observed integer values must not yet be called a block type, version, length, checksum, or object count without independent validation.

## Next experiments

1. Group blocks by their complete preamble bytes and payload signature.
2. Compare candidate header lengths across each group.
3. Check whether candidate length fields match actual block spans or decompressed sizes.
4. Validate Zstandard frame boundaries and decompressed output sizes.
5. Compare repeated block families across multiple independently-created test worlds, without publishing their contents.
6. Change one controlled in-game property at a time and compare local before/after files. This is the preferred way to assign meaning to fields.

A field is considered understood only after its interpretation predicts the same result across multiple samples or controlled changes.


## Header field grouping from the local world sample

A byte-level comparison of all 20 `S2BH` occurrences in the local sample shows a repeated 12-byte prefix:

| Relative offset | Width | Observation |
|---:|---:|---|
| 0 | 4 bytes | ASCII marker `S2BH` |
| 4 | 4 bytes | `02 00 00 00` in all 20 occurrences |
| 8 | 2 bytes | Varies by block family |
| 10 | 2 bytes | Varies by block family |

The two 16-bit values at relative offsets 8 and 10 form useful grouping keys. Their meaning is not yet known, so the implementation should call them raw fields rather than type IDs until confirmed.

Observed raw field pairs (little-endian unsigned 16-bit values) include:

| Field A | Field B | Occurrences |
|---:|---:|---:|
| 2 | 2 | 10 |
| 3 | 1 | 1 |
| 4 | 2 | 1 |
| 5 | 1 | 1 |
| 6 | 100 | 1 |
| 7 | 1 | 1 |
| 8 | 1 | 1 |
| 11 | 2 | 1 |
| 12 | 3 | 1 |
| 13 | 1 | 1 |
| 14 | 1 | 1 |
| 3 | 21 | 1 |

The repeated value at relative offset 4 may be a format/version field, but this is only a hypothesis. It must be compared with other game versions before assigning that meaning.

### Zstandard placement

For the three directly observed Zstandard frames, the frame magic begins 14 bytes after the corresponding `S2BH` marker. This suggests a 14-byte preamble for those particular blocks:

- 4-byte marker
- 4-byte repeated value
- 2-byte field A
- 2-byte field B
- 2 additional bytes before the Zstandard frame

This does **not** prove that all block families use a 14-byte header. Other block families need separate boundary and payload analysis.

### Important correction to the scanner model

The scanner's current candidate spans are only ranges between consecutive marker occurrences. They must not yet be treated as confirmed top-level block lengths. A future parser should first validate the container-level index/table and each block's own declared boundaries, if present.
