from unittest.mock import AsyncMock
from unittest.mock import patch

import pytest
import ctypes
import ipaddress

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


@pytest.mark.asyncio
async def test_decode_int32(int32_case):
    decoded, encoded, desc = int32_case

    with patch(
        "spoe_forge.spop.decoders.data_types._parse_varint", new_callable=AsyncMock
    ) as mock_parse:
        # _parse_varint returns the raw varint value before ctypes conversion
        # For negative numbers, this is the unsigned representation
        if decoded >= 0:
            raw_value = decoded
        else:
            # Convert negative to unsigned representation
            raw_value = ctypes.c_uint32(decoded).value

        mock_parse.return_value = (raw_value, len(encoded))

        result = await data_type.decode_int32(encoded, 0)

        mock_parse.assert_called_once_with(encoded, 0)
        assert result == (decoded, len(encoded))


@pytest.mark.asyncio
async def test_decode_int32_calls_parse_varint():
    """Verify decode_int32 calls _parse_varint with correct parameters."""
    buf = b"\x01\x02\x03"
    offset = 1

    with patch(
        "spoe_forge.spop.decoders.data_types._parse_varint", new_callable=AsyncMock
    ) as mock_parse:
        mock_parse.return_value = (42, 3)
        await data_type.decode_int32(buf, offset)
        mock_parse.assert_called_once_with(buf, offset)


@pytest.mark.asyncio
async def test_decode_uint32(uint32_case):
    decoded, encoded, desc = uint32_case

    with patch(
        "spoe_forge.spop.decoders.data_types._parse_varint", new_callable=AsyncMock
    ) as mock_parse:
        mock_parse.return_value = (decoded, len(encoded))

        result = await data_type.decode_uint32(encoded, 0)

        mock_parse.assert_called_once_with(encoded, 0)
        assert result == (decoded, len(encoded))


@pytest.mark.asyncio
async def test_decode_uint32_calls_parse_varint():
    """Verify decode_uint32 calls _parse_varint with correct parameters."""
    buf = b"\x01\x02\x03"
    offset = 2

    with patch(
        "spoe_forge.spop.decoders.data_types._parse_varint", new_callable=AsyncMock
    ) as mock_parse:
        mock_parse.return_value = (100, 4)
        await data_type.decode_uint32(buf, offset)
        mock_parse.assert_called_once_with(buf, offset)


@pytest.mark.asyncio
async def test_decode_int64(int64_case):
    decoded, encoded, desc = int64_case

    with patch(
        "spoe_forge.spop.decoders.data_types._parse_varint", new_callable=AsyncMock
    ) as mock_parse:
        # _parse_varint returns the raw varint value before ctypes conversion
        if decoded >= 0:
            raw_value = decoded
        else:
            # Convert negative to unsigned representation
            raw_value = ctypes.c_uint64(decoded).value

        mock_parse.return_value = (raw_value, len(encoded))

        result = await data_type.decode_int64(encoded, 0)

        mock_parse.assert_called_once_with(encoded, 0)
        assert result == (decoded, len(encoded))


@pytest.mark.asyncio
async def test_decode_int64_calls_parse_varint():
    """Verify decode_int64 calls _parse_varint with correct parameters."""
    buf = b"\xff" * 10
    offset = 5

    with patch(
        "spoe_forge.spop.decoders.data_types._parse_varint", new_callable=AsyncMock
    ) as mock_parse:
        mock_parse.return_value = (999, 8)
        await data_type.decode_int64(buf, offset)
        mock_parse.assert_called_once_with(buf, offset)


@pytest.mark.asyncio
async def test_decode_uint64(uint64_case):
    decoded, encoded, desc = uint64_case

    with patch(
        "spoe_forge.spop.decoders.data_types._parse_varint", new_callable=AsyncMock
    ) as mock_parse:
        mock_parse.return_value = (decoded, len(encoded))

        result = await data_type.decode_uint64(encoded, 0)

        mock_parse.assert_called_once_with(encoded, 0)
        assert result == (decoded, len(encoded))


@pytest.mark.asyncio
async def test_decode_uint64_calls_parse_varint():
    """Verify decode_uint64 calls _parse_varint with correct parameters."""
    buf = b"\x00\x00\x00"
    offset = 0

    with patch(
        "spoe_forge.spop.decoders.data_types._parse_varint", new_callable=AsyncMock
    ) as mock_parse:
        mock_parse.return_value = (1234567890, 5)
        await data_type.decode_uint64(buf, offset)
        mock_parse.assert_called_once_with(buf, offset)


@pytest.mark.asyncio
async def test_decode_ipv4(ipv4_case):
    decoded, encoded, desc = ipv4_case

    result = await data_type.decode_ipv4(encoded, 0)
    assert result == (decoded, 4)


@pytest.mark.asyncio
async def test_decode_ipv4_with_offset():
    """Test decode_ipv4 with non-zero offset."""
    buf = b"\xff\xff" + b"\xc0\xa8\x01\x01"
    result = await data_type.decode_ipv4(buf, 2)
    assert result == (ipaddress.IPv4Address("192.168.1.1"), 6)


@pytest.mark.parametrize(
    "buf,offset",
    [
        (b"", 0),
        (b"\x00", 0),
        (b"\x00\x00", 0),
        (b"\x00\x00\x00", 0),
        (b"\x00\x00\x00\x00", 1),  # offset=1, need 4 more bytes, only have 3
    ],
)
@pytest.mark.asyncio
async def test_decode_ipv4_raises_error(buf, offset):
    """Test decode_ipv4 raises error on insufficient data."""
    with pytest.raises(SpopDecodeError, match="unexpected end of stream decoding ipv4"):
        await data_type.decode_ipv4(buf, offset)


@pytest.mark.asyncio
async def test_decode_ipv6(ipv6_case):
    decoded, encoded, desc = ipv6_case

    result = await data_type.decode_ipv6(encoded, 0)
    assert result == (decoded, 16)


@pytest.mark.asyncio
async def test_decode_ipv6_with_offset():
    """Test decode_ipv6 with non-zero offset."""
    buf = b"\xff\xff" + b"\x00" * 14 + b"\x00\x01"
    result = await data_type.decode_ipv6(buf, 2)
    assert result == (ipaddress.IPv6Address("::1"), 18)


@pytest.mark.parametrize(
    "buf,offset",
    [
        (b"", 0),
        (b"\x00" * 10, 0),
        (b"\x00" * 15, 0),
        (b"\x00" * 20, 5),  # offset puts us 1 byte short
    ],
)
@pytest.mark.asyncio
async def test_decode_ipv6_raises_error(buf, offset):
    """Test decode_ipv6 raises error on insufficient data."""
    with pytest.raises(SpopDecodeError, match="unexpected end of stream decoding ipv6"):
        await data_type.decode_ipv6(buf, offset)


@pytest.mark.asyncio
async def test_decode_binary(binary_case):
    decoded, encoded, desc = binary_case

    with patch(
        "spoe_forge.spop.decoders.data_types._parse_varint", new_callable=AsyncMock
    ) as mock_parse:
        # _parse_varint returns (length, offset_after_length)
        data_len = len(decoded)
        len_bytes = len(encoded) - data_len
        mock_parse.return_value = (data_len, len_bytes)

        result = await data_type.decode_binary(encoded, 0)

        mock_parse.assert_called_once_with(encoded, 0)
        assert result == (decoded, len(encoded))


@pytest.mark.asyncio
async def test_decode_binary_with_offset():
    """Test decode_binary with non-zero offset."""
    buf = b"\xff\xff" + b"\x03abc"
    with patch(
        "spoe_forge.spop.decoders.data_types._parse_varint", new_callable=AsyncMock
    ) as mock_parse:
        mock_parse.return_value = (3, 3)  # length=3, offset after varint=3
        result = await data_type.decode_binary(buf, 2)
        mock_parse.assert_called_once_with(buf, 2)
        assert result == (b"abc", 6)


@pytest.mark.asyncio
async def test_decode_binary_raises_error_on_short_buffer():
    """Test decode_binary raises error when buffer is too short for declared length."""
    buf = b"\x0a\x00\x00"  # Says 10 bytes, but only has 2
    with patch(
        "spoe_forge.spop.decoders.data_types._parse_varint", new_callable=AsyncMock
    ) as mock_parse:
        mock_parse.return_value = (10, 1)
        with pytest.raises(SpopDecodeError):
            await data_type.decode_binary(buf, 0)


@pytest.mark.asyncio
async def test_decode_string(string_case):
    decoded, encoded, desc = string_case

    with patch(
        "spoe_forge.spop.decoders.data_types.decode_binary", new_callable=AsyncMock
    ) as mock_binary:
        mock_binary.return_value = (decoded.encode("ascii"), len(encoded))

        result = await data_type.decode_string(encoded, 0)

        mock_binary.assert_called_once_with(encoded, 0)
        assert result == (decoded, len(encoded))


@pytest.mark.asyncio
async def test_decode_string_with_offset():
    """Test decode_string with non-zero offset."""
    buf = b"\xff\xff\x05hello"
    with patch(
        "spoe_forge.spop.decoders.data_types.decode_binary", new_callable=AsyncMock
    ) as mock_binary:
        mock_binary.return_value = (b"hello", 7)
        result = await data_type.decode_string(buf, 2)
        mock_binary.assert_called_once_with(buf, 2)
        assert result == ("hello", 7)


@pytest.mark.asyncio
async def test_decode_string_raises_error_on_invalid_ascii():
    """Test decode_string raises error on non-ASCII bytes."""
    with patch(
        "spoe_forge.spop.decoders.data_types.decode_binary", new_callable=AsyncMock
    ) as mock_binary:
        # Return invalid ASCII (high bit set)
        mock_binary.return_value = (b"\xff\xfe", 3)
        with pytest.raises(
            SpopDecodeError, match="invalid ASCII string in SPOP stream"
        ):
            await data_type.decode_string(b"\x02\xff\xfe", 0)


@pytest.mark.asyncio
async def test_decode_bool(bool_case):
    decoded, encoded, desc = bool_case

    result = await data_type.decode_bool(encoded, 0)
    assert result == (decoded, 1)


@pytest.mark.asyncio
async def test_decode_bool_with_offset():
    """Test decode_bool with non-zero offset."""
    # 0x11 = True (DataType.BOOL | DataFlag.BOOL_TRUE)
    buf = b"\xff\xff\x11"
    result = await data_type.decode_bool(buf, 2)
    assert result == (True, 3)


@pytest.mark.asyncio
async def test_decode_bool_raises_error_on_empty_buffer():
    """Test decode_bool raises error on empty buffer."""
    with pytest.raises(SpopDecodeError):
        await data_type.decode_bool(b"", 0)


@pytest.mark.asyncio
async def test_decode_bool_raises_error_on_out_of_bounds():
    """Test decode_bool raises error when offset is out of bounds."""
    with pytest.raises(SpopDecodeError):
        await data_type.decode_bool(b"\x01", 1)


@pytest.mark.asyncio
async def test_auto_decode_var_null():
    """Test auto_decode_var with NULL type."""

    # DataType.NULL == 0x00
    buf = b"\x00"
    result = await data_type.auto_decode_var(buf, 0)
    assert result == (None, 1)


@pytest.mark.asyncio
async def test_auto_decode_var_bool_true():
    """Test auto_decode_var with BOOL type (True)."""

    # DataType.BOOL | DataFlag.BOOL_TRUE == 0x11
    buf = b"\x11"
    with patch(
        "spoe_forge.spop.decoders.data_types.decode_bool", new_callable=AsyncMock
    ) as mock_bool:
        mock_bool.return_value = (True, 1)
        result = await data_type.auto_decode_var(buf, 0)
        # decode_bool gets called with offset-1 since we already consumed the type byte
        mock_bool.assert_called_once_with(buf, 0)
        assert result == (True, 1)


@pytest.mark.asyncio
async def test_auto_decode_var_bool_false():
    """Test auto_decode_var with BOOL type (False)."""

    # DataType.BOOL == 0x01
    buf = b"\x01"
    with patch(
        "spoe_forge.spop.decoders.data_types.decode_bool", new_callable=AsyncMock
    ) as mock_bool:
        mock_bool.return_value = (False, 1)
        result = await data_type.auto_decode_var(buf, 0)
        mock_bool.assert_called_once_with(buf, 0)
        assert result == (False, 1)


@pytest.mark.asyncio
async def test_auto_decode_var_int32():
    """Test auto_decode_var with INT32 type."""

    # DataType.INT32 == 0x02
    buf = b"\x02\x01"
    with patch(
        "spoe_forge.spop.decoders.data_types.decode_int32", new_callable=AsyncMock
    ) as mock_int32:
        mock_int32.return_value = (42, 2)
        result = await data_type.auto_decode_var(buf, 0)
        mock_int32.assert_called_once_with(buf, 1)
        assert result == (42, 2)


@pytest.mark.asyncio
async def test_auto_decode_var_uint32():
    """Test auto_decode_var with UINT32 type."""

    # DataType.UINT32 == 0x03
    buf = b"\x03\x01"
    with patch(
        "spoe_forge.spop.decoders.data_types.decode_uint32", new_callable=AsyncMock
    ) as mock_uint32:
        mock_uint32.return_value = (100, 2)
        result = await data_type.auto_decode_var(buf, 0)
        mock_uint32.assert_called_once_with(buf, 1)
        assert result == (100, 2)


@pytest.mark.asyncio
async def test_auto_decode_var_int64():
    """Test auto_decode_var with INT64 type."""

    # DataType.INT64 == 0x04
    buf = b"\x04\x01"
    with patch(
        "spoe_forge.spop.decoders.data_types.decode_int64", new_callable=AsyncMock
    ) as mock_int64:
        mock_int64.return_value = (999999, 2)
        result = await data_type.auto_decode_var(buf, 0)
        mock_int64.assert_called_once_with(buf, 1)
        assert result == (999999, 2)


@pytest.mark.asyncio
async def test_auto_decode_var_uint64():
    """Test auto_decode_var with UINT64 type."""

    # DataType.UINT64 == 0x05
    buf = b"\x05\x01"
    with patch(
        "spoe_forge.spop.decoders.data_types.decode_uint64", new_callable=AsyncMock
    ) as mock_uint64:
        mock_uint64.return_value = (888888, 2)
        result = await data_type.auto_decode_var(buf, 0)
        mock_uint64.assert_called_once_with(buf, 1)
        assert result == (888888, 2)


@pytest.mark.asyncio
async def test_auto_decode_var_ipv4():
    """Test auto_decode_var with IPv4 type."""

    # DataType.IPV4 == 0x06
    buf = b"\x06\xc0\xa8\x01\x01"
    with patch(
        "spoe_forge.spop.decoders.data_types.decode_ipv4", new_callable=AsyncMock
    ) as mock_ipv4:
        mock_ipv4.return_value = (ipaddress.IPv4Address("192.168.1.1"), 5)
        result = await data_type.auto_decode_var(buf, 0)
        mock_ipv4.assert_called_once_with(buf, 1)
        assert result == (ipaddress.IPv4Address("192.168.1.1"), 5)


@pytest.mark.asyncio
async def test_auto_decode_var_ipv6():
    """Test auto_decode_var with IPv6 type."""

    # DataType.IPV6 == 0x07
    buf = b"\x07" + b"\x00" * 16
    with patch(
        "spoe_forge.spop.decoders.data_types.decode_ipv6", new_callable=AsyncMock
    ) as mock_ipv6:
        mock_ipv6.return_value = (ipaddress.IPv6Address("::"), 17)
        result = await data_type.auto_decode_var(buf, 0)
        mock_ipv6.assert_called_once_with(buf, 1)
        assert result == (ipaddress.IPv6Address("::"), 17)


@pytest.mark.asyncio
async def test_auto_decode_var_string():
    """Test auto_decode_var with STRING type."""

    # DataType.STRING == 0x08
    buf = b"\x08\x05hello"
    with patch(
        "spoe_forge.spop.decoders.data_types.decode_string", new_callable=AsyncMock
    ) as mock_string:
        mock_string.return_value = ("hello", 7)
        result = await data_type.auto_decode_var(buf, 0)
        mock_string.assert_called_once_with(buf, 1)
        assert result == ("hello", 7)


@pytest.mark.asyncio
async def test_auto_decode_var_binary():
    """Test auto_decode_var with BINARY type."""

    # DataType.BINARY == 0x09
    buf = b"\x09\x03abc"
    with patch(
        "spoe_forge.spop.decoders.data_types.decode_binary", new_callable=AsyncMock
    ) as mock_binary:
        mock_binary.return_value = (b"abc", 5)
        result = await data_type.auto_decode_var(buf, 0)
        mock_binary.assert_called_once_with(buf, 1)
        assert result == (b"abc", 5)


@pytest.mark.asyncio
async def test_auto_decode_var_with_offset():
    """Test auto_decode_var with non-zero offset."""

    # DataType.NULL == 0x00
    buf = b"\xff\xff\x00"
    result = await data_type.auto_decode_var(buf, 2)
    assert result == (None, 3)


@pytest.mark.asyncio
async def test_auto_decode_var_raises_error_on_empty_buffer():
    """Test auto_decode_var raises error when buffer is too short."""
    with pytest.raises(
        SpopDecodeError, match="unexpected end of stream reading data type"
    ):
        await data_type.auto_decode_var(b"", 0)


@pytest.mark.asyncio
async def test_auto_decode_var_raises_error_on_out_of_bounds():
    """Test auto_decode_var raises error when offset is out of bounds."""
    with pytest.raises(
        SpopDecodeError, match="unexpected end of stream reading data type"
    ):
        await data_type.auto_decode_var(b"\x00", 1)


@pytest.mark.asyncio
async def test_auto_decode_var_raises_error_on_unknown_type():
    """Test auto_decode_var raises error on unknown data type."""

    # Use an invalid type value (0x0A is beyond BINARY=9)
    buf = b"\x0a"
    with pytest.raises(SpopDecodeError, match="unknown data type"):
        await data_type.auto_decode_var(buf, 0)
