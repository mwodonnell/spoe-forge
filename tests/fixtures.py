import ipaddress

import pytest


@pytest.fixture(
    # (Decoded val, Encoded val, Num Bytes, Description
    params=[
        (0, b"\x00", 1, "Integer 0"),
        (1, b"\x01", 1, "Integer 1"),
        (239, b"\xef", 1, "Integer 239"),
        (240, b"\xf0\x00", 2, "Integer 240"),
        (241, b"\xf1\x00", 2, "Integer 241"),
        (2287, b"\xff\x7f", 2, "Integer 2,287"),
        (2288, b"\xf0\x80\x00", 3, "Integer 2,288"),
        (2289, b"\xf1\x80\x00", 3, "Integer 2,289"),
        (264431, b"\xff\xff\x7f", 3, "Integer 264,431"),
        (264432, b"\xf0\x80\x80\x00", 4, "Integer 264,432"),
        (264433, b"\xf1\x80\x80\x00", 4, "Integer 264,433"),
        (33818863, b"\xff\xff\xff\x7f", 4, "Integer 33,818,863"),
        (33818864, b"\xf0\x80\x80\x80\x00", 5, "Integer 33,818,864"),
        (33818865, b"\xf1\x80\x80\x80\x00", 5, "Integer 33,818,865"),
        (4328786159, b"\xff\xff\xff\xff\x7f", 5, "Integer 4,328,786,159"),
    ],
    ids=lambda case: case[3],
)
def varint_case(request):
    """Provides (decoded, encoded, num bytes, desc) for each param."""
    return request.param


@pytest.fixture(
    params=[
        # (buf, offset)
        (b"", 0),
        (b"\xff", 1),
        (b"\xff\xff", 2),
    ]
)
def unexpected_end_of_stream_case(request):
    """Provides (buf, out of bounds offset) for each param."""
    return request.param


@pytest.fixture(
    # (Decoded val, Encoded val, Description
    params=[
        (0, b"\x00", "Integer 0"),
        (1, b"\x01", "Integer 1"),
        (255, b"\xff", "Integer 255"),
    ],
    ids=lambda case: case[2],
)
def tiny_int_case(request):
    """Provides (decoded, encoded, desc) for each param."""
    return request.param


@pytest.fixture(
    # (Decoded val, Encoded val, Description
    params=[
        (0, b"\x00\x00\x00\x00", "Integer 0"),
        (255, b"\x00\x00\x00\xff", "Integer 255"),
        (4278190080, b"\xff\x00\x00\x00", "Integer 4278190080"),
        (4278190335, b"\xff\x00\x00\xff", "Integer 4278190335"),
    ],
    ids=lambda case: case[2],
)
def frame_len_case(request):
    """Provides (decoded, encoded, desc) for each param."""
    return request.param


@pytest.fixture(
    # (Decoded val, Encoded val, Description)
    params=[
        (0, b"\x00\x00\x00\x00", "INT32: 0"),
        (1, b"\x00\x00\x00\x01", "INT32: 1"),
        (239, b"\x00\x00\x00\xef", "INT32: 239"),
        (2147483647, b"\xff\xff\xff\xff\x7f", "INT32: max positive (2^31 - 1)"),
        (-1, b"\xff\xff\xff\xff\x0f", "INT32: -1"),
        (-2147483648, b"\x80\x80\x80\x80\x08", "INT32: min negative (-2^31)"),
    ],
    ids=lambda case: case[2],
)
def int32_case(request):
    """Provides (decoded, encoded, desc) for INT32 test cases."""
    return request.param


@pytest.fixture(
    # (Decoded val, Encoded val, Description)
    params=[
        (0, b"\x00", "UINT32: 0"),
        (1, b"\x01", "UINT32: 1"),
        (239, b"\xef", "UINT32: 239"),
        (4294967295, b"\xff\xff\xff\xff\x0f", "UINT32: max (2^32 - 1)"),
    ],
    ids=lambda case: case[2],
)
def uint32_case(request):
    """Provides (decoded, encoded, desc) for UINT32 test cases."""
    return request.param


@pytest.fixture(
    # (Decoded val, Encoded val, Description)
    params=[
        (0, b"\x00", "INT64: 0"),
        (1, b"\x01", "INT64: 1"),
        (239, b"\xef", "INT64: 239"),
        (
            9223372036854775807,
            b"\xff\xff\xff\xff\xff\xff\xff\xff\x7f",
            "INT64: max positive (2^63 - 1)",
        ),
        (-1, b"\xff\xff\xff\xff\xff\xff\xff\xff\x0f", "INT64: -1"),
        (
            -9223372036854775808,
            b"\x80\x80\x80\x80\x80\x80\x80\x80\x08",
            "INT64: min negative (-2^63)",
        ),
    ],
    ids=lambda case: case[2],
)
def int64_case(request):
    """Provides (decoded, encoded, desc) for INT64 test cases."""
    return request.param


@pytest.fixture(
    # (Decoded val, Encoded val, Description)
    params=[
        (0, b"\x00", "UINT64: 0"),
        (1, b"\x01", "UINT64: 1"),
        (239, b"\xef", "UINT64: 239"),
        (
            18446744073709551615,
            b"\xff\xff\xff\xff\xff\xff\xff\xff\x0f",
            "UINT64: max (2^64 - 1)",
        ),
    ],
    ids=lambda case: case[2],
)
def uint64_case(request):
    """Provides (decoded, encoded, desc) for UINT64 test cases."""
    return request.param


@pytest.fixture(
    # (Decoded val, Encoded val, Description)
    params=[
        (ipaddress.IPv4Address("0.0.0.0"), b"\x00\x00\x00\x00", "IPv4: 0.0.0.0"),
        (ipaddress.IPv4Address("127.0.0.1"), b"\x7f\x00\x00\x01", "IPv4: 127.0.0.1"),
        (
            ipaddress.IPv4Address("192.168.1.1"),
            b"\xc0\xa8\x01\x01",
            "IPv4: 192.168.1.1",
        ),
        (
            ipaddress.IPv4Address("255.255.255.255"),
            b"\xff\xff\xff\xff",
            "IPv4: 255.255.255.255",
        ),
    ],
    ids=lambda case: case[2],
)
def ipv4_case(request):
    """Provides (decoded, encoded, desc) for IPv4 test cases."""
    return request.param


@pytest.fixture(
    # (Decoded val, Encoded val, Description)
    params=[
        (
            ipaddress.IPv6Address("::"),
            b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00",
            "IPv6: ::",
        ),
        (
            ipaddress.IPv6Address("::1"),
            b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01",
            "IPv6: ::1",
        ),
        (
            ipaddress.IPv6Address("2001:db8::1"),
            b"\x20\x01\x0d\xb8\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01",
            "IPv6: 2001:db8::1",
        ),
        (
            ipaddress.IPv6Address("ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff"),
            b"\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff",
            "IPv6: ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff",
        ),
    ],
    ids=lambda case: case[2],
)
def ipv6_case(request):
    """Provides (decoded, encoded, desc) for IPv6 test cases."""
    return request.param


@pytest.fixture(
    # (Decoded val, Encoded val, Description)
    params=[
        (b"", b"\x00", "Binary: empty"),
        (b"\x00", b"\x01\x00", "Binary: single null byte"),
        (b"hello", b"\x05hello", "Binary: 'hello'"),
        (b"\xff\xfe\xfd", b"\x03\xff\xfe\xfd", "Binary: 3 bytes of data"),
        (b"a" * 240, b"\xf0\x00" + b"a" * 240, "Binary: 240 bytes (varint size 2)"),
    ],
    ids=lambda case: case[2],
)
def binary_case(request):
    """Provides (decoded, encoded, desc) for binary test cases."""
    return request.param


@pytest.fixture(
    # (Decoded val, Encoded val, Description)
    params=[
        ("", b"\x00", "String: empty"),
        ("hello", b"\x05hello", "String: 'hello'"),
        ("test123", b"\x07test123", "String: 'test123'"),
        ("a" * 239, b"\xef" + b"a" * 239, "String: 239 characters (varint size 1)"),
    ],
    ids=lambda case: case[2],
)
def string_case(request):
    """Provides (decoded, encoded, desc) for string test cases."""
    return request.param


@pytest.fixture(
    # (Decoded val, Encoded val, Description)
    # Note: Bool values are encoded in the type byte itself
    # DataType.BOOL (0x01) | DataFlag.BOOL_TRUE (0x10) = 0x11 for True
    # DataType.BOOL (0x01) = 0x01 for False
    params=[
        (True, b"\x11", "Bool: True"),
        (False, b"\x01", "Bool: False"),
    ],
    ids=lambda case: case[2],
)
def bool_case(request):
    """Provides (decoded, encoded, desc) for boolean test cases."""
    return request.param
