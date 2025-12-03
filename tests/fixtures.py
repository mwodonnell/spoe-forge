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
