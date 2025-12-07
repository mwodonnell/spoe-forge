"""Round-trip tests for SPOP data type encoding and decoding.

These tests encode data using encoders and then decode it back to verify
the full code path works correctly without mocking.
"""

import ipaddress

import pytest

from spoe_forge.spop.decoders import data_types as decoder
from spoe_forge.spop.encoders import data_types as encoder


@pytest.mark.asyncio
async def test_roundtrip_varint(varint_case):
    """Test varint encoding/decoding round-trip."""
    decoded_value, _, _, desc = varint_case

    # Encode
    encoded = await encoder._compose_varint(decoded_value)

    # Decode
    result, offset = await decoder._parse_varint(encoded, 0)

    assert result == decoded_value
    assert offset == len(encoded)


@pytest.mark.asyncio
async def test_roundtrip_tiny_int(tiny_int_case):
    """Test tiny int encoding/decoding round-trip."""
    decoded_value, _, desc = tiny_int_case

    # Encode
    encoded = await encoder.encode_tiny_int(decoded_value)

    # Decode
    result, offset = await decoder.decode_tiny_int(encoded, 0)

    assert result == decoded_value
    assert offset == 1


@pytest.mark.asyncio
async def test_roundtrip_frame_len(frame_len_case):
    """Test frame length encoding/decoding round-trip."""
    decoded_value, _, desc = frame_len_case

    # Encode
    encoded = await encoder.encode_frame_len(decoded_value)

    # Decode
    result = await decoder.decode_frame_len(encoded)

    assert result == decoded_value


@pytest.mark.asyncio
async def test_roundtrip_int32(int32_case):
    """Test INT32 encoding/decoding round-trip."""
    decoded_value, _, desc = int32_case

    # Encode (with type byte)
    encoded = await encoder.encode_dt_int32(decoded_value)

    # Decode (skip type byte)
    result, offset = await decoder.decode_int32(encoded, 1)

    assert result == decoded_value
    assert offset == len(encoded)


@pytest.mark.asyncio
async def test_roundtrip_uint32(uint32_case):
    """Test UINT32 encoding/decoding round-trip."""
    decoded_value, _, desc = uint32_case

    # Encode (with type byte)
    encoded = await encoder.encode_dt_uint32(decoded_value)

    # Decode (skip type byte)
    result, offset = await decoder.decode_uint32(encoded, 1)

    assert result == decoded_value
    assert offset == len(encoded)


@pytest.mark.asyncio
async def test_roundtrip_int64(int64_case):
    """Test INT64 encoding/decoding round-trip."""
    decoded_value, _, desc = int64_case

    # Encode
    encoded = await encoder.encode_dt_int64(decoded_value)

    # Decode (skip type byte)
    result, offset = await decoder.decode_int64(encoded, 1)

    assert result == decoded_value
    assert offset == len(encoded)


@pytest.mark.asyncio
async def test_roundtrip_uint64(uint64_case):
    """Test UINT64 encoding/decoding round-trip."""
    decoded_value, _, desc = uint64_case

    # Encode
    encoded = await encoder.encode_dt_uint64(decoded_value)

    # Decode (skip type byte)
    result, offset = await decoder.decode_uint64(encoded, 1)

    assert result == decoded_value
    assert offset == len(encoded)


@pytest.mark.asyncio
async def test_roundtrip_bool(bool_case):
    """Test boolean encoding/decoding round-trip."""
    decoded_value, _, desc = bool_case

    # Encode (includes type byte)
    encoded = await encoder.encode_dt_bool(decoded_value)

    # Decode (from type byte)
    result, offset = await decoder.decode_bool(encoded, 0)

    assert result == decoded_value
    assert offset == 1


@pytest.mark.asyncio
async def test_roundtrip_ipv4(ipv4_case):
    """Test IPv4 encoding/decoding round-trip."""
    decoded_value, _, desc = ipv4_case

    # Encode
    encoded = await encoder.encode_dt_ipv4(decoded_value)

    # Decode (skip type byte)
    result, offset = await decoder.decode_ipv4(encoded, 1)

    assert result == decoded_value
    assert offset == 5  # 1 (type) + 4 (ipv4)


@pytest.mark.asyncio
async def test_roundtrip_ipv6(ipv6_case):
    """Test IPv6 encoding/decoding round-trip."""
    decoded_value, _, desc = ipv6_case

    # Encode
    encoded = await encoder.encode_dt_ipv6(decoded_value)

    # Decode (skip type byte)
    result, offset = await decoder.decode_ipv6(encoded, 1)

    assert result == decoded_value
    assert offset == 17  # 1 (type) + 16 (ipv6)


@pytest.mark.asyncio
async def test_roundtrip_binary(binary_case):
    """Test binary encoding/decoding round-trip."""
    decoded_value, _, desc = binary_case

    # Encode
    encoded = await encoder._compose_binary(decoded_value)

    # Decode
    result, offset = await decoder.decode_binary(encoded, 0)

    assert result == decoded_value
    assert offset == len(encoded)


@pytest.mark.asyncio
async def test_roundtrip_string(string_case):
    """Test string encoding/decoding round-trip."""
    decoded_value, _, desc = string_case

    # Encode
    encoded = await encoder.encode_string(decoded_value)

    # Decode
    result, offset = await decoder.decode_string(encoded, 0)

    assert result == decoded_value
    assert offset == len(encoded)


@pytest.mark.asyncio
async def test_roundtrip_typed_null():
    """Test NULL typed data encoding/decoding round-trip."""
    # Encode
    encoded = await encoder.encode_dt_null()

    # Decode
    result, offset = await decoder.auto_decode_var(encoded, 0)

    assert result is None
    assert offset == 1


@pytest.mark.asyncio
async def test_roundtrip_typed_bool_true():
    """Test BOOL (True) typed data encoding/decoding round-trip."""
    # Encode
    encoded = await encoder.encode_dt_bool(True)

    # Decode
    result, offset = await decoder.auto_decode_var(encoded, 0)

    assert result is True
    assert offset == 1


@pytest.mark.asyncio
async def test_roundtrip_typed_bool_false():
    """Test BOOL (False) typed data encoding/decoding round-trip."""
    # Encode
    encoded = await encoder.encode_dt_bool(False)

    # Decode
    result, offset = await decoder.auto_decode_var(encoded, 0)

    assert result is False
    assert offset == 1


@pytest.mark.asyncio
async def test_roundtrip_typed_int32():
    """Test INT32 typed data encoding/decoding round-trip."""
    value = 42

    # Encode
    encoded = await encoder.encode_dt_int32(value)

    # Decode
    result, offset = await decoder.auto_decode_var(encoded, 0)

    assert result == value
    assert offset == len(encoded)


@pytest.mark.asyncio
async def test_roundtrip_typed_uint32():
    """Test UINT32 typed data encoding/decoding round-trip."""
    value = 12345

    # Encode
    encoded = await encoder.encode_dt_uint32(value)

    # Decode
    result, offset = await decoder.auto_decode_var(encoded, 0)

    assert result == value
    assert offset == len(encoded)


@pytest.mark.asyncio
async def test_roundtrip_typed_int64():
    """Test INT64 typed data encoding/decoding round-trip."""
    value = 4328786159  # Max value that fits in varint (< 4328786160)

    # Encode
    encoded = await encoder.encode_dt_int64(value)

    # Decode
    result, offset = await decoder.auto_decode_var(encoded, 0)

    assert result == value
    assert offset == len(encoded)


@pytest.mark.asyncio
async def test_roundtrip_typed_uint64():
    """Test UINT64 typed data encoding/decoding round-trip."""
    value = 4328786159  # Max value that fits in varint (< 4328786160)

    # Encode
    encoded = await encoder.encode_dt_uint64(value)

    # Decode
    result, offset = await decoder.auto_decode_var(encoded, 0)

    assert result == value
    assert offset == len(encoded)


@pytest.mark.asyncio
async def test_roundtrip_typed_ipv4():
    """Test IPv4 typed data encoding/decoding round-trip."""
    value = ipaddress.IPv4Address("192.168.1.100")

    # Encode
    encoded = await encoder.encode_dt_ipv4(value)

    # Decode
    result, offset = await decoder.auto_decode_var(encoded, 0)

    assert result == value
    assert offset == 5  # 1 (type) + 4 (ipv4)


@pytest.mark.asyncio
async def test_roundtrip_typed_ipv6():
    """Test IPv6 typed data encoding/decoding round-trip."""
    value = ipaddress.IPv6Address("2001:db8::8a2e:370:7334")

    # Encode
    encoded = await encoder.encode_dt_ipv6(value)

    # Decode
    result, offset = await decoder.auto_decode_var(encoded, 0)

    assert result == value
    assert offset == 17  # 1 (type) + 16 (ipv6)


@pytest.mark.asyncio
async def test_roundtrip_typed_binary():
    """Test BINARY typed data encoding/decoding round-trip."""
    value = b"\x00\x01\x02\xff\xfe\xfd"

    # Encode
    encoded = await encoder.encode_dt_binary(value)

    # Decode
    result, offset = await decoder.auto_decode_var(encoded, 0)

    assert result == value
    assert offset == len(encoded)


@pytest.mark.asyncio
async def test_roundtrip_typed_string():
    """Test STRING typed data encoding/decoding round-trip."""
    value = "Hello, SPOE!"

    # Encode
    encoded = await encoder.encode_dt_string(value)

    # Decode
    result, offset = await decoder.auto_decode_var(encoded, 0)

    assert result == value
    assert offset == len(encoded)


@pytest.mark.asyncio
async def test_roundtrip_auto_encode_null():
    """Test auto_encode_dt_var with None round-trip."""
    value = None

    # Encode
    encoded = await encoder.auto_encode_dt_var(value)

    # Decode
    result, offset = await decoder.auto_decode_var(encoded, 0)

    assert result is None
    assert offset == 1


@pytest.mark.asyncio
async def test_roundtrip_auto_encode_bool():
    """Test auto_encode_dt_var with bool round-trip."""
    for value in [True, False]:
        # Encode
        encoded = await encoder.auto_encode_dt_var(value)

        # Decode
        result, offset = await decoder.auto_decode_var(encoded, 0)

        assert result is value
        assert offset == 1


@pytest.mark.asyncio
async def test_roundtrip_auto_encode_int():
    """Test auto_encode_dt_var with int round-trip."""
    # Test values that fit within varint limits when converted to unsigned
    test_values = [
        0,
        1,
        42,
        -1,  # Becomes 0xFFFFFFFFFFFFFFFF but fits in uint64->ctypes
        2147483647,  # Max int32
        -2147483648,  # Min int32 - becomes large unsigned, may fail
    ]

    for value in test_values:
        # Encode (as INT64)
        encoded = await encoder.auto_encode_dt_var(value)

        # Decode
        result, offset = await decoder.auto_decode_var(encoded, 0)

        assert result == value
        assert offset == len(encoded)


@pytest.mark.asyncio
async def test_roundtrip_auto_encode_ipv4():
    """Test auto_encode_dt_var with IPv4 round-trip."""
    value = ipaddress.IPv4Address("10.0.0.1")

    # Encode
    encoded = await encoder.auto_encode_dt_var(value)

    # Decode
    result, offset = await decoder.auto_decode_var(encoded, 0)

    assert result == value
    assert offset == 5


@pytest.mark.asyncio
async def test_roundtrip_auto_encode_ipv6():
    """Test auto_encode_dt_var with IPv6 round-trip."""
    value = ipaddress.IPv6Address("fe80::1")

    # Encode
    encoded = await encoder.auto_encode_dt_var(value)

    # Decode
    result, offset = await decoder.auto_decode_var(encoded, 0)

    assert result == value
    assert offset == 17


@pytest.mark.asyncio
async def test_roundtrip_auto_encode_bytes():
    """Test auto_encode_dt_var with bytes round-trip."""
    value = b"binary data \x00\xff"

    # Encode
    encoded = await encoder.auto_encode_dt_var(value)

    # Decode
    result, offset = await decoder.auto_decode_var(encoded, 0)

    assert result == value
    assert offset == len(encoded)


@pytest.mark.asyncio
async def test_roundtrip_auto_encode_string():
    """Test auto_encode_dt_var with string round-trip."""
    value = "test string"

    # Encode
    encoded = await encoder.auto_encode_dt_var(value)

    # Decode
    result, offset = await decoder.auto_decode_var(encoded, 0)

    assert result == value
    assert offset == len(encoded)


@pytest.mark.asyncio
async def test_roundtrip_complex_data():
    """Test round-trip with various complex edge cases."""
    test_cases = [
        # Empty values
        ("", "empty string"),
        (b"", "empty bytes"),
        # Boundary values
        (0, "zero int"),
        (239, "239 - varint boundary"),
        (240, "240 - varint 2-byte start"),
        (2287, "2287 - varint boundary"),
        (2288, "2288 - varint 3-byte start"),
        # IP addresses
        (ipaddress.IPv4Address("0.0.0.0"), "IPv4 zero"),
        (ipaddress.IPv4Address("255.255.255.255"), "IPv4 max"),
        (ipaddress.IPv6Address("::"), "IPv6 zero"),
        (ipaddress.IPv6Address("ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff"), "IPv6 max"),
        # Special strings
        ("a" * 239, "239 char string - varint boundary"),
        ("a" * 240, "240 char string - varint 2-byte"),
    ]

    for value, description in test_cases:
        # Encode
        encoded = await encoder.auto_encode_dt_var(value)

        # Decode
        result, offset = await decoder.auto_decode_var(encoded, 0)

        assert result == value, f"Failed for {description}"
        assert offset == len(encoded), f"Offset mismatch for {description}"


@pytest.mark.asyncio
async def test_roundtrip_with_offset():
    """Test round-trip with non-zero offset."""
    value = "test"
    prefix = b"\xff\xff"  # Some dummy data

    # Encode
    encoded_data = await encoder.auto_encode_dt_var(value)
    full_buffer = prefix + encoded_data

    # Decode from offset
    result, offset = await decoder.auto_decode_var(full_buffer, len(prefix))

    assert result == value
    assert offset == len(full_buffer)


@pytest.mark.asyncio
async def test_roundtrip_multiple_values():
    """Test encoding/decoding multiple values in sequence."""
    values = [
        42,
        "hello",
        True,
        ipaddress.IPv4Address("192.168.1.1"),
        b"binary",
        None,
        False,
    ]

    # Encode all values
    buffer = b""
    for value in values:
        encoded = await encoder.auto_encode_dt_var(value)
        buffer += encoded

    # Decode all values
    offset = 0
    decoded_values = []
    for _ in values:
        result, offset = await decoder.auto_decode_var(buffer, offset)
        decoded_values.append(result)

    assert decoded_values == values
    assert offset == len(buffer)
