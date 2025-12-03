import pytest
from spoe_forge.spop.decoders import data_types as data_type
from spoe_forge.spop.exception import SpopDecodeError


@pytest.mark.asyncio
async def test_parse_varint(varint_case):
    decoded, encoded, num_bytes, desc = varint_case

    result = await data_type._parse_varint(encoded)
    assert result == (decoded, num_bytes)


@pytest.mark.asyncio
async def test_parse_varint_raises_error(unexpected_end_of_stream_case):
    buf, offset = unexpected_end_of_stream_case
    with pytest.raises(SpopDecodeError):
        await data_type._parse_varint(buf, offset)


@pytest.mark.asyncio
async def test_parse_tint_int(tiny_int_case):
    decoded, encoded, desc = tiny_int_case

    result = await data_type.decode_tiny_int(encoded)
    assert result == (decoded, 1)


@pytest.mark.asyncio
async def test_parse_tiny_int_raises_error(unexpected_end_of_stream_case):
    buf, offset = unexpected_end_of_stream_case
    with pytest.raises(SpopDecodeError):
        await data_type.decode_tiny_int(buf, offset)


@pytest.mark.asyncio
async def test_decode_frame_len(frame_len_case):
    decoded, encoded, desc = frame_len_case

    assert decoded == await data_type.decode_frame_len(encoded)


@pytest.mark.parametrize(
    "buf",
    [
        b"\x00",
        b"\x00\x00",
        b"\x00\x00\x00",
        b"\x00\x00\x00\x00\x00",
    ],
)
@pytest.mark.asyncio
async def test_decode_frame_len_raises_error(buf):
    with pytest.raises(SpopDecodeError):
        await data_type.decode_frame_len(buf)
