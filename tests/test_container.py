from shroudtools.container import BLOCK_MAGIC, FILE_MAGIC, ZSTD_MAGIC, inspect_bytes


def test_recognizes_sv2c_and_block_candidates():
    data = (
        FILE_MAGIC
        + b"header"
        + BLOCK_MAGIC
        + b"\x00" * 12
        + ZSTD_MAGIC
        + b"compressed-placeholder"
        + BLOCK_MAGIC
        + b"second-block"
    )

    result = inspect_bytes(data, "synthetic.ksd")

    assert result.has_expected_magic is True
    assert result.block_marker_count == 2
    assert len(result.blocks) == 2
    assert result.blocks[0].offset == data.index(BLOCK_MAGIC)
    assert result.blocks[0].zstd_frame_offsets == (16,)
    assert result.blocks[1].span_size == len(b"S2BHsecond-block")


def test_does_not_require_known_magic():
    result = inspect_bytes(b"not-a-savegame", "unknown.bin")

    assert result.has_expected_magic is False
    assert result.block_marker_count == 0
    assert result.blocks == ()
