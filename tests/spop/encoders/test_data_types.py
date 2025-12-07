from unittest.mock import AsyncMock
from unittest.mock import patch

import ipaddress
import pytest

from spoe_forge.spop.encoders import data_types as data_type
from spoe_forge.spop.exception import SpopEncodeError


@pytest.mark.asyncio
async def test_compose_varint(varint_case):
    decoded, encoded, num_bytes, desc = varint_case

    result = await data_type._compose_varint(decoded)
    assert result == encoded
    assert num_bytes == len(encoded)


@pytest.mark.parametrize("value", [-1, 4328786160])
@pytest.mark.asyncio
async def test_compose_varint_raises_error(value):
    # Expected to raise an encode error as these are out of bounds
    with pytest.raises(SpopEncodeError):
        await data_type._compose_varint(value)


@pytest.mark.asyncio
async def test_encode_tiny_int(tiny_int_case):
    decoded, encoded, desc = tiny_int_case

    result = await data_type.encode_tiny_int(decoded)
    assert result == encoded


@pytest.mark.parametrize("value", [-1, 256, 1000])
@pytest.mark.asyncio
async def test_encode_tiny_int_raises_error(value):
    """Test encode_tiny_int raises error for out of range values."""
    with pytest.raises(SpopEncodeError, match="tiny int must be 0-255"):
        await data_type.encode_tiny_int(value)


@pytest.mark.asyncio
async def test_encode_frame_len(frame_len_case):
    decoded, encoded, desc = frame_len_case

    result = await data_type.encode_frame_len(decoded)
    assert result == encoded


@pytest.mark.parametrize("value", [-1, 2**32])
@pytest.mark.asyncio
async def test_encode_frame_len_raises_error(value):
    """Test encode_frame_len raises error for values outside uint32 range."""
    with pytest.raises(SpopEncodeError, match="failed to encode frame_len int"):
        await data_type.encode_frame_len(value)


@pytest.mark.asyncio
async def test_encode_int():
    """Test encode_int delegates to _compose_varint."""
    with patch(
        "spoe_forge.spop.encoders.data_types._compose_varint", new_callable=AsyncMock
    ) as mock_varint:
        mock_varint.return_value = b"\x42"
        result = await data_type.encode_int(100)
        mock_varint.assert_called_once_with(100)
        assert result == b"\x42"


@pytest.mark.asyncio
async def test_encode_string(string_case):
    decoded, encoded, desc = string_case

    result = await data_type.encode_string(decoded)
    assert result == encoded


@pytest.mark.asyncio
async def test_encode_string_calls_compose_binary():
    """Test encode_string calls _compose_binary with ASCII bytes."""
    with patch(
        "spoe_forge.spop.encoders.data_types._compose_binary", new_callable=AsyncMock
    ) as mock_binary:
        mock_binary.return_value = b"\x05hello"
        result = await data_type.encode_string("hello")
        mock_binary.assert_called_once_with(b"hello")
        assert result == b"\x05hello"


@pytest.mark.asyncio
async def test_encode_string_raises_error_on_non_ascii():
    """Test encode_string raises error for non-ASCII strings."""
    with pytest.raises(SpopEncodeError, match="cannot encode non-ASCII string"):
        await data_type.encode_string("héllo")


@pytest.mark.asyncio
async def test_compose_binary(binary_case):
    decoded, encoded, desc = binary_case

    result = await data_type._compose_binary(decoded)
    assert result == encoded


@pytest.mark.asyncio
async def test_compose_binary_calls_compose_varint():
    """Test _compose_binary calls _compose_varint for length."""
    with patch(
        "spoe_forge.spop.encoders.data_types._compose_varint", new_callable=AsyncMock
    ) as mock_varint:
        mock_varint.return_value = b"\x05"
        result = await data_type._compose_binary(b"hello")
        mock_varint.assert_called_once_with(5)
        assert result == b"\x05hello"


@pytest.mark.asyncio
async def test_type_data_null():
    """Test _type_data creates correct type byte for NULL."""
    result = await data_type._type_data(0x00)  # DataType.NULL
    assert result == b"\x00"


@pytest.mark.asyncio
async def test_type_data_bool_with_flag():
    """Test _type_data creates correct type byte for BOOL with flag."""
    result = await data_type._type_data(0x01, 0x10)  # DataType.BOOL, DataFlag.BOOL_TRUE
    assert result == b"\x11"


@pytest.mark.asyncio
async def test_type_data_int32():
    """Test _type_data creates correct type byte for INT32."""
    result = await data_type._type_data(0x02)  # DataType.INT32
    assert result == b"\x02"


@pytest.mark.asyncio
async def test_encode_dt_null():
    """Test encode_dt_null creates NULL type byte."""
    result = await data_type.encode_dt_null()
    assert result == b"\x00"


@pytest.mark.asyncio
async def test_encode_dt_null_calls_type_data():
    """Test encode_dt_null calls _type_data."""
    with patch(
        "spoe_forge.spop.encoders.data_types._type_data", new_callable=AsyncMock
    ) as mock_type:
        mock_type.return_value = b"\x00"
        result = await data_type.encode_dt_null()
        mock_type.assert_called_once()
        assert result == b"\x00"


@pytest.mark.asyncio
async def test_encode_dt_int32():
    """Test encode_dt_int32 with type prefix."""
    with (
        patch(
            "spoe_forge.spop.encoders.data_types._type_data", new_callable=AsyncMock
        ) as mock_type,
        patch(
            "spoe_forge.spop.encoders.data_types.encode_int", new_callable=AsyncMock
        ) as mock_int,
    ):
        mock_type.return_value = b"\x02"
        mock_int.return_value = b"\x2a"
        result = await data_type.encode_dt_int32(42)
        mock_int.assert_called_once_with(42)
        assert result == b"\x02\x2a"


@pytest.mark.asyncio
async def test_encode_dt_uint32():
    """Test encode_dt_uint32 with type prefix."""
    with (
        patch(
            "spoe_forge.spop.encoders.data_types._type_data", new_callable=AsyncMock
        ) as mock_type,
        patch(
            "spoe_forge.spop.encoders.data_types.encode_int", new_callable=AsyncMock
        ) as mock_int,
    ):
        mock_type.return_value = b"\x03"
        mock_int.return_value = b"\x64"
        result = await data_type.encode_dt_uint32(100)
        mock_int.assert_called_once_with(100)
        assert result == b"\x03\x64"


@pytest.mark.asyncio
async def test_encode_dt_int64():
    """Test encode_dt_int64 with type prefix."""
    with (
        patch(
            "spoe_forge.spop.encoders.data_types._type_data", new_callable=AsyncMock
        ) as mock_type,
        patch(
            "spoe_forge.spop.encoders.data_types.encode_int", new_callable=AsyncMock
        ) as mock_int,
    ):
        mock_type.return_value = b"\x04"
        mock_int.return_value = b"\xff\xff\x7f"
        result = await data_type.encode_dt_int64(2287)
        mock_int.assert_called_once_with(2287)
        assert result == b"\x04\xff\xff\x7f"


@pytest.mark.asyncio
async def test_encode_dt_uint64():
    """Test encode_dt_uint64 with type prefix."""
    with (
        patch(
            "spoe_forge.spop.encoders.data_types._type_data", new_callable=AsyncMock
        ) as mock_type,
        patch(
            "spoe_forge.spop.encoders.data_types.encode_int", new_callable=AsyncMock
        ) as mock_int,
    ):
        mock_type.return_value = b"\x05"  # DataType.UINT64
        mock_int.return_value = b"\x01"
        result = await data_type.encode_dt_uint64(1)
        mock_int.assert_called_once_with(1)
        assert result == b"\x05\x01"


@pytest.mark.asyncio
async def test_encode_dt_bool_true():
    """Test encode_dt_bool with True value."""
    result = await data_type.encode_dt_bool(True)
    assert result == b"\x11"  # DataType.BOOL | DataFlag.BOOL_TRUE


@pytest.mark.asyncio
async def test_encode_dt_bool_false():
    """Test encode_dt_bool with False value."""
    result = await data_type.encode_dt_bool(False)
    assert result == b"\x01"  # DataType.BOOL (no flag)


@pytest.mark.asyncio
async def test_encode_dt_bool_calls_type_data():
    """Test encode_dt_bool calls _type_data with correct flag."""
    with patch(
        "spoe_forge.spop.encoders.data_types._type_data", new_callable=AsyncMock
    ) as mock_type:
        mock_type.return_value = b"\x11"
        result = await data_type.encode_dt_bool(True)
        # Should call with DataType.BOOL and DataFlag.BOOL_TRUE
        assert mock_type.call_count == 1
        assert result == b"\x11"


@pytest.mark.asyncio
async def test_encode_dt_ipv4(ipv4_case):
    """Test encode_dt_ipv4 with type prefix."""
    decoded, encoded_no_type, desc = ipv4_case

    result = await data_type.encode_dt_ipv4(decoded)
    # Should be: type byte (0x06) + 4 bytes of IP
    assert result == b"\x06" + encoded_no_type
    assert len(result) == 5


@pytest.mark.asyncio
async def test_encode_dt_ipv4_calls_type_data():
    """Test encode_dt_ipv4 calls _type_data."""
    with patch(
        "spoe_forge.spop.encoders.data_types._type_data", new_callable=AsyncMock
    ) as mock_type:
        mock_type.return_value = b"\x06"
        addr = ipaddress.IPv4Address("192.168.1.1")
        result = await data_type.encode_dt_ipv4(addr)
        mock_type.assert_called_once()
        assert result == b"\x06" + addr.packed


@pytest.mark.asyncio
async def test_encode_dt_ipv6(ipv6_case):
    """Test encode_dt_ipv6 with type prefix."""
    decoded, encoded_no_type, desc = ipv6_case

    result = await data_type.encode_dt_ipv6(decoded)
    # Should be: type byte (0x07) + 16 bytes of IP
    assert result == b"\x07" + encoded_no_type
    assert len(result) == 17


@pytest.mark.asyncio
async def test_encode_dt_ipv6_calls_type_data():
    """Test encode_dt_ipv6 calls _type_data."""
    with patch(
        "spoe_forge.spop.encoders.data_types._type_data", new_callable=AsyncMock
    ) as mock_type:
        mock_type.return_value = b"\x07"
        addr = ipaddress.IPv6Address("::1")
        result = await data_type.encode_dt_ipv6(addr)
        mock_type.assert_called_once()
        assert result == b"\x07" + addr.packed


@pytest.mark.asyncio
async def test_encode_dt_binary(binary_case):
    """Test encode_dt_binary with type prefix."""
    decoded, encoded_no_type, desc = binary_case

    result = await data_type.encode_dt_binary(decoded)
    # Should be: type byte (0x09) + length varint + data
    assert result == b"\x09" + encoded_no_type


@pytest.mark.asyncio
async def test_encode_dt_binary_calls_compose_binary():
    """Test encode_dt_binary calls _compose_binary."""
    with (
        patch(
            "spoe_forge.spop.encoders.data_types._type_data", new_callable=AsyncMock
        ) as mock_type,
        patch(
            "spoe_forge.spop.encoders.data_types._compose_binary",
            new_callable=AsyncMock,
        ) as mock_binary,
    ):
        mock_type.return_value = b"\x09"
        mock_binary.return_value = b"\x03abc"
        result = await data_type.encode_dt_binary(b"abc")
        mock_binary.assert_called_once_with(b"abc")
        assert result == b"\x09\x03abc"


@pytest.mark.asyncio
async def test_encode_dt_string(string_case):
    """Test encode_dt_string with type prefix."""
    decoded, encoded_no_type, desc = string_case

    result = await data_type.encode_dt_string(decoded)
    # Should be: type byte (0x08) + length varint + ASCII data
    assert result == b"\x08" + encoded_no_type


@pytest.mark.asyncio
async def test_encode_dt_string_calls_compose_binary():
    """Test encode_dt_string calls _compose_binary with ASCII bytes."""
    with (
        patch(
            "spoe_forge.spop.encoders.data_types._type_data", new_callable=AsyncMock
        ) as mock_type,
        patch(
            "spoe_forge.spop.encoders.data_types._compose_binary",
            new_callable=AsyncMock,
        ) as mock_binary,
    ):
        mock_type.return_value = b"\x08"
        mock_binary.return_value = b"\x05hello"
        result = await data_type.encode_dt_string("hello")
        mock_binary.assert_called_once_with(b"hello")
        assert result == b"\x08\x05hello"


@pytest.mark.asyncio
async def test_encode_dt_string_raises_error_on_non_ascii():
    """Test encode_dt_string raises error for non-ASCII strings."""
    with pytest.raises(SpopEncodeError, match="cannot encode non-ASCII string"):
        await data_type.encode_dt_string("héllo")


@pytest.mark.asyncio
async def test_auto_encode_dt_var_null():
    """Test auto_encode_dt_var with None."""
    with patch(
        "spoe_forge.spop.encoders.data_types.encode_dt_null", new_callable=AsyncMock
    ) as mock_null:
        mock_null.return_value = b"\x00"
        result = await data_type.auto_encode_dt_var(None)
        mock_null.assert_called_once()
        assert result == b"\x00"


@pytest.mark.asyncio
async def test_auto_encode_dt_var_bool_true():
    """Test auto_encode_dt_var with bool True."""
    with patch(
        "spoe_forge.spop.encoders.data_types.encode_dt_bool", new_callable=AsyncMock
    ) as mock_bool:
        mock_bool.return_value = b"\x11"
        result = await data_type.auto_encode_dt_var(True)
        mock_bool.assert_called_once_with(True)
        assert result == b"\x11"


@pytest.mark.asyncio
async def test_auto_encode_dt_var_bool_false():
    """Test auto_encode_dt_var with bool False."""
    with patch(
        "spoe_forge.spop.encoders.data_types.encode_dt_bool", new_callable=AsyncMock
    ) as mock_bool:
        mock_bool.return_value = b"\x01"
        result = await data_type.auto_encode_dt_var(False)
        mock_bool.assert_called_once_with(False)
        assert result == b"\x01"


@pytest.mark.asyncio
async def test_auto_encode_dt_var_int():
    """Test auto_encode_dt_var with int."""
    # Note: All ints are encoded as INT64
    with patch(
        "spoe_forge.spop.encoders.data_types.encode_dt_int64", new_callable=AsyncMock
    ) as mock_int64:
        mock_int64.return_value = b"\x04\x2a"
        result = await data_type.auto_encode_dt_var(42)
        mock_int64.assert_called_once_with(42)
        assert result == b"\x04\x2a"


@pytest.mark.asyncio
async def test_auto_encode_dt_var_ipv4():
    """Test auto_encode_dt_var with IPv4 address."""
    addr = ipaddress.IPv4Address("192.168.1.1")
    with patch(
        "spoe_forge.spop.encoders.data_types.encode_dt_ipv4", new_callable=AsyncMock
    ) as mock_ipv4:
        mock_ipv4.return_value = b"\x06\xc0\xa8\x01\x01"
        result = await data_type.auto_encode_dt_var(addr)
        mock_ipv4.assert_called_once_with(addr)
        assert result == b"\x06\xc0\xa8\x01\x01"


@pytest.mark.asyncio
async def test_auto_encode_dt_var_ipv6():
    """Test auto_encode_dt_var with IPv6 address."""
    addr = ipaddress.IPv6Address("::1")
    with patch(
        "spoe_forge.spop.encoders.data_types.encode_dt_ipv6", new_callable=AsyncMock
    ) as mock_ipv6:
        mock_ipv6.return_value = b"\x07" + b"\x00" * 15 + b"\x01"
        await data_type.auto_encode_dt_var(addr)
        mock_ipv6.assert_called_once_with(addr)


@pytest.mark.asyncio
async def test_auto_encode_dt_var_bytes():
    """Test auto_encode_dt_var with bytes."""
    with patch(
        "spoe_forge.spop.encoders.data_types.encode_dt_binary", new_callable=AsyncMock
    ) as mock_binary:
        mock_binary.return_value = b"\x09\x03abc"
        result = await data_type.auto_encode_dt_var(b"abc")
        mock_binary.assert_called_once_with(b"abc")
        assert result == b"\x09\x03abc"


@pytest.mark.asyncio
async def test_auto_encode_dt_var_string():
    """Test auto_encode_dt_var with string."""
    with patch(
        "spoe_forge.spop.encoders.data_types.encode_dt_string", new_callable=AsyncMock
    ) as mock_string:
        mock_string.return_value = b"\x08\x05hello"
        result = await data_type.auto_encode_dt_var("hello")
        mock_string.assert_called_once_with("hello")
        assert result == b"\x08\x05hello"


@pytest.mark.asyncio
async def test_auto_encode_dt_var_bool_priority_over_int():
    """Test that bools are correctly encoded as BOOL, not INT64."""
    # In Python, bool is a subclass of int
    # We need to check isinstance(val, bool) BEFORE isinstance(val, int)
    # This ensures bools are correctly encoded as BOOL instead of INT64
    result = await data_type.auto_encode_dt_var(True)
    # Should encode as BOOL (0x11)
    assert result == b"\x11"

    result = await data_type.auto_encode_dt_var(False)
    # Should encode as BOOL (0x01)
    assert result == b"\x01"


@pytest.mark.asyncio
async def test_auto_encode_dt_var_raises_error_on_unsupported_type():
    """Test auto_encode_dt_var raises error for unsupported types."""
    with pytest.raises(SpopEncodeError, match="cannot encode unsupported type"):
        await data_type.auto_encode_dt_var([1, 2, 3])  # list is not supported


@pytest.mark.asyncio
async def test_auto_encode_dt_var_raises_error_on_dict():
    """Test auto_encode_dt_var raises error for dict."""
    with pytest.raises(SpopEncodeError, match="cannot encode unsupported type"):
        await data_type.auto_encode_dt_var({"key": "value"})


@pytest.mark.asyncio
async def test_auto_encode_dt_var_raises_error_on_float():
    """Test auto_encode_dt_var raises error for float."""
    with pytest.raises(SpopEncodeError, match="cannot encode unsupported type"):
        await data_type.auto_encode_dt_var(3.14)
