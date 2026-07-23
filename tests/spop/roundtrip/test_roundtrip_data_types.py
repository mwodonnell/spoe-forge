import ipaddress

import pytest

from spoe_forge.spop.decoders import data_types as decoder
from spoe_forge.spop.encoders import data_types as encoder


@pytest.mark.asyncio
async def test_roundtrip_varint(varint_case):
    decoded_value, _, _, _ = varint_case

    encoded = await encoder._compose_varint(decoded_value)
    result, offset = decoder._parse_varint(encoded, 0)

    assert result == decoded_value
    assert offset == len(encoded)


@pytest.mark.asyncio
async def test_roundtrip_tiny_int(tiny_int_case):
    decoded_value, _, _ = tiny_int_case

    encoded = await encoder.encode_tiny_int(decoded_value)
    result, offset = decoder.decode_tiny_int(encoded, 0)

    assert result == decoded_value
    assert offset == 1


@pytest.mark.asyncio
async def test_roundtrip_frame_len(frame_len_case):
    decoded_value, _, _ = frame_len_case

    encoded = await encoder.encode_frame_len(decoded_value)
    result = decoder.decode_frame_len(encoded)

    assert result == decoded_value


@pytest.mark.asyncio
async def test_roundtrip_int32(int32_case):
    decoded_value, _, _ = int32_case

    encoded = await encoder.encode_dt_int32(decoded_value)
    result, offset = decoder.decode_int32(encoded, 1)

    assert result == decoded_value
    assert offset == len(encoded)


@pytest.mark.asyncio
async def test_roundtrip_uint32(uint32_case):
    decoded_value, _, _ = uint32_case

    encoded = await encoder.encode_dt_uint32(decoded_value)
    result, offset = decoder.decode_uint32(encoded, 1)

    assert result == decoded_value
    assert offset == len(encoded)


@pytest.mark.asyncio
async def test_roundtrip_int64(int64_case):
    decoded_value, _, _ = int64_case

    encoded = await encoder.encode_dt_int64(decoded_value)
    result, offset = decoder.decode_int64(encoded, 1)

    assert result == decoded_value
    assert offset == len(encoded)


@pytest.mark.asyncio
async def test_roundtrip_uint64(uint64_case):
    decoded_value, _, _ = uint64_case

    encoded = await encoder.encode_dt_uint64(decoded_value)
    result, offset = decoder.decode_uint64(encoded, 1)

    assert result == decoded_value
    assert offset == len(encoded)


@pytest.mark.asyncio
async def test_roundtrip_bool(bool_case):
    decoded_value, _, _ = bool_case

    encoded = await encoder.encode_dt_bool(decoded_value)
    result, offset = decoder.decode_bool(encoded, 0)

    assert result == decoded_value
    assert offset == 1


@pytest.mark.asyncio
async def test_roundtrip_ipv4(ipv4_case):
    decoded_value, _, _ = ipv4_case

    encoded = await encoder.encode_dt_ipv4(decoded_value)
    result, offset = decoder.decode_ipv4(encoded, 1)

    assert result == decoded_value
    assert offset == 5  # 1 (type) + 4 (ipv4)


@pytest.mark.asyncio
async def test_roundtrip_ipv6(ipv6_case):
    decoded_value, _, _ = ipv6_case

    encoded = await encoder.encode_dt_ipv6(decoded_value)
    result, offset = decoder.decode_ipv6(encoded, 1)

    assert result == decoded_value
    assert offset == 17  # 1 (type) + 16 (ipv6)


@pytest.mark.asyncio
async def test_roundtrip_binary(binary_case):
    decoded_value, _, _ = binary_case

    encoded = await encoder._compose_binary(decoded_value)
    result, offset = decoder.decode_binary(encoded, 0)

    assert result == decoded_value
    assert offset == len(encoded)


@pytest.mark.asyncio
async def test_roundtrip_string(string_case):
    decoded_value, _, _ = string_case

    encoded = await encoder.encode_string(decoded_value)
    result, offset = decoder.decode_string(encoded, 0)

    assert result == decoded_value
    assert offset == len(encoded)


@pytest.mark.asyncio
async def test_roundtrip_typed_null():
    encoded = await encoder.encode_dt_null()
    result, offset = decoder.auto_decode_var(encoded, 0)

    assert result is None
    assert offset == 1


@pytest.mark.asyncio
async def test_roundtrip_typed_bool_true():
    encoded = await encoder.encode_dt_bool(True)
    result, offset = decoder.auto_decode_var(encoded, 0)

    assert result is True
    assert offset == 1


@pytest.mark.asyncio
async def test_roundtrip_typed_bool_false():
    encoded = await encoder.encode_dt_bool(False)
    result, offset = decoder.auto_decode_var(encoded, 0)

    assert result is False
    assert offset == 1


@pytest.mark.asyncio
async def test_roundtrip_typed_int32():
    value = 42

    encoded = await encoder.encode_dt_int32(value)
    result, offset = decoder.auto_decode_var(encoded, 0)

    assert result == value
    assert offset == len(encoded)


@pytest.mark.asyncio
async def test_roundtrip_typed_uint32():
    value = 12345

    encoded = await encoder.encode_dt_uint32(value)
    result, offset = decoder.auto_decode_var(encoded, 0)

    assert result == value
    assert offset == len(encoded)


@pytest.mark.asyncio
async def test_roundtrip_typed_int64():
    value = 4328786159

    encoded = await encoder.encode_dt_int64(value)
    result, offset = decoder.auto_decode_var(encoded, 0)

    assert result == value
    assert offset == len(encoded)


@pytest.mark.asyncio
async def test_roundtrip_typed_uint64():
    value = 4328786159

    encoded = await encoder.encode_dt_uint64(value)
    result, offset = decoder.auto_decode_var(encoded, 0)

    assert result == value
    assert offset == len(encoded)


@pytest.mark.asyncio
async def test_roundtrip_typed_ipv4():
    value = ipaddress.IPv4Address("192.168.1.100")

    encoded = await encoder.encode_dt_ipv4(value)
    result, offset = decoder.auto_decode_var(encoded, 0)

    assert result == value
    assert offset == 5  # 1 (type) + 4 (ipv4)


@pytest.mark.asyncio
async def test_roundtrip_typed_ipv6():
    value = ipaddress.IPv6Address("2001:db8::8a2e:370:7334")

    encoded = await encoder.encode_dt_ipv6(value)
    result, offset = decoder.auto_decode_var(encoded, 0)

    assert result == value
    assert offset == 17  # 1 (type) + 16 (ipv6)


@pytest.mark.asyncio
async def test_roundtrip_typed_binary():
    value = b"\x00\x01\x02\xff\xfe\xfd"

    encoded = await encoder.encode_dt_binary(value)
    result, offset = decoder.auto_decode_var(encoded, 0)

    assert result == value
    assert offset == len(encoded)


@pytest.mark.asyncio
async def test_roundtrip_typed_string():
    value = "Hello, SPOE!"

    encoded = await encoder.encode_dt_string(value)
    result, offset = decoder.auto_decode_var(encoded, 0)

    assert result == value
    assert offset == len(encoded)


@pytest.mark.asyncio
async def test_roundtrip_auto_encode_null():
    value = None

    encoded = await encoder.auto_encode_dt_var(value)
    result, offset = decoder.auto_decode_var(encoded, 0)

    assert result is None
    assert offset == 1


@pytest.mark.asyncio
async def test_roundtrip_auto_encode_bool():
    for value in [True, False]:
        encoded = await encoder.auto_encode_dt_var(value)
        result, offset = decoder.auto_decode_var(encoded, 0)

        assert result is value
        assert offset == 1


@pytest.mark.asyncio
async def test_roundtrip_auto_encode_int():
    # Test values that fit within varint limits when converted to unsigned
    test_values = [
        0,
        1,
        42,
        -1,
        2147483647,
        -2147483648,
    ]

    for value in test_values:
        encoded = await encoder.auto_encode_dt_var(value)
        result, offset = decoder.auto_decode_var(encoded, 0)

        assert result == value
        assert offset == len(encoded)


@pytest.mark.asyncio
async def test_roundtrip_auto_encode_ipv4():
    value = ipaddress.IPv4Address("10.0.0.1")

    encoded = await encoder.auto_encode_dt_var(value)
    result, offset = decoder.auto_decode_var(encoded, 0)

    assert result == value
    assert offset == 5


@pytest.mark.asyncio
async def test_roundtrip_auto_encode_ipv6():
    value = ipaddress.IPv6Address("fe80::1")

    encoded = await encoder.auto_encode_dt_var(value)
    result, offset = decoder.auto_decode_var(encoded, 0)

    assert result == value
    assert offset == 17


@pytest.mark.asyncio
async def test_roundtrip_auto_encode_bytes():
    value = b"binary data \x00\xff"

    encoded = await encoder.auto_encode_dt_var(value)
    result, offset = decoder.auto_decode_var(encoded, 0)

    assert result == value
    assert offset == len(encoded)


@pytest.mark.asyncio
async def test_roundtrip_auto_encode_string():
    value = "test string"

    encoded = await encoder.auto_encode_dt_var(value)
    result, offset = decoder.auto_decode_var(encoded, 0)

    assert result == value
    assert offset == len(encoded)


@pytest.mark.asyncio
async def test_roundtrip_complex_data():
    test_cases = [
        ("", "empty string"),
        (b"", "empty bytes"),
        (0, "zero int"),
        (239, "239 - varint boundary"),
        (240, "240 - varint 2-byte start"),
        (2287, "2287 - varint boundary"),
        (2288, "2288 - varint 3-byte start"),
        (ipaddress.IPv4Address("0.0.0.0"), "IPv4 zero"),
        (ipaddress.IPv4Address("255.255.255.255"), "IPv4 max"),
        (ipaddress.IPv6Address("::"), "IPv6 zero"),
        (ipaddress.IPv6Address("ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff"), "IPv6 max"),
        ("a" * 239, "239 char string - varint boundary"),
        ("a" * 240, "240 char string - varint 2-byte"),
    ]

    for value, description in test_cases:
        encoded = await encoder.auto_encode_dt_var(value)
        result, offset = decoder.auto_decode_var(encoded, 0)

        assert result == value, f"Failed for {description}"
        assert offset == len(encoded), f"Offset mismatch for {description}"


@pytest.mark.asyncio
async def test_roundtrip_with_offset():
    value = "test"
    prefix = b"\xff\xff"  # Some dummy data

    encoded_data = await encoder.auto_encode_dt_var(value)
    full_buffer = prefix + encoded_data

    result, offset = decoder.auto_decode_var(full_buffer, len(prefix))

    assert result == value
    assert offset == len(full_buffer)


@pytest.mark.asyncio
async def test_roundtrip_multiple_values():
    values = [
        42,
        "hello",
        True,
        ipaddress.IPv4Address("192.168.1.1"),
        b"binary",
        None,
        False,
    ]

    buffer = b""
    for value in values:
        encoded = await encoder.auto_encode_dt_var(value)
        buffer += encoded

    offset = 0
    decoded_values = []
    for _ in values:
        result, offset = decoder.auto_decode_var(buffer, offset)
        decoded_values.append(result)

    assert decoded_values == values
    assert offset == len(buffer)
