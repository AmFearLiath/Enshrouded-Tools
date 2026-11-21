# Entity snapshot and transform research

Status: research notes; not an implemented decoder.

## Scope

ShroudTools' Local World Scanner needs to recover placed entities and their transforms from a world save. The outer SV2C container reader identifies an entity snapshot chunk, but the inner ECS snapshot format is not yet decoded.

These notes distinguish public engine research from observations made on any individual save. No user savegame data, world names, coordinates, object names, identifiers, offsets, hashes, or extracted payloads belong in this document.

## Public engine findings

The public `matenm/emf-enshrouded` reverse-engineering project documents the following for the game build it analyzed:

- The world save pipeline creates an ECS world snapshot.
- The snapshot serializes a component type table and entity chunks.
- The ECS snapshot code walks an entity chunk/sector table and serializes dirty chunks, or reuses cached serialized blobs.
- The world writer stores entities and base data as distinct data groups.
- The documented engine has 37 components marked `savegame_relevant`; examples include `CurrentTransform`, `Inventory`, and `InventorySetup`.
- The engine's `CurrentTransform` component contains a `WorldTransform` value.

The same project documents the following transform representation:

| Field | Representation |
|---|---|
| Position | Three signed 64-bit values |
| Position scale | 32.32 fixed point; meters = value / 2^32 |
| Orientation | Quaternion |
| Scale | Three 32-bit floats |
| Total transform size | 56 bytes |

These are engine-level findings from the referenced project and build. They are not proof that the serialized bytes in every SV2C save use the same field order or encoding. ShroudTools must validate the on-disk representation independently before decoding values.

## Implications for ShroudTools

The first entity decoder should be built in layers:

1. Decode the entity snapshot's type table.
2. Decode serialized entity chunks and their component membership.
3. Map serialized component identifiers to component types.
4. Decode only the first required components, starting with `CurrentTransform`.
5. Preserve unknown component payloads without interpreting or dropping them.
6. Join entity records to base/building metadata only after the relationship is established from evidence.

The initial target is deliberately narrow: entities with a valid transform and enough identity/template information to classify them as placed objects. Inventory decoding is a later step.

## Differential validation plan

A decoder must not be accepted based on plausible-looking coordinates alone. Validate it using controlled save pairs:

- Save A: a stable world state.
- Save B: same world after moving exactly one known placed object.
- Save C: same world after placing exactly one additional object.
- Optional Save D: same world after removing that object.

Compare the entity snapshot and related base data between each pair. A candidate transform field is accepted only if the moved object's decoded position changes consistently and unrelated entities remain stable. A candidate entity record is accepted only if the added/removed object appears or disappears as expected.

All test saves remain local and must never be committed to GitHub. Public tests use synthetic byte fixtures only.

## References

- [matenm/emf-enshrouded — engine map](https://github.com/matenm/emf-enshrouded/blob/main/docs/ENGINE_MAP.md)
- [matenm/emf-enshrouded — save/load and ECS snapshot research](https://github.com/matenm/emf-enshrouded/blob/main/docs/engine_parts/plumbing.md)
- [matenm/emf-enshrouded — reflection and component metadata research](https://github.com/matenm/emf-enshrouded/blob/main/docs/engine_parts/re_reflection.md)

## Current unknowns

- Exact on-disk layout of the entity snapshot type table.
- Exact on-disk layout and record boundaries of serialized entity chunks.
- Whether the analyzed public engine build matches the game build that produced a given save.
- Exact mapping between entity templates, base/building records, and placed construction objects.
- Which entity types correspond to chests and other searchable containers.

Until these are resolved, ShroudTools must report unknown or partial records rather than fabricate object identities or positions.
