from unittest.mock import patch

import ipaddress
import pytest

from spoe_forge.spop.encoders import data_types as data_type
from spoe_forge.spop.exception import SpopEncodeError


def test_compose_varint(varint_case):
    decoded, encoded, num_bytes, desc = varint_case
    result = data_type._compose_varint(decoded)

    assert result == encoded
    assert num_bytes == len(encoded)


def test_compose_varint_raises_error_negative():
    with pytest.raises(SpopEncodeError, match="cannot encode negative number"):
        data_type._compose_varint(-1)


@pytest.mark.parametrize(
    "value,expected_bytes",
    [
        (4328786160, 6),
        (18446744073709551615, 10),  # 2^64 - 1
    ],
)
def test_compose_varint_large_values(value, expected_bytes):
    result = data_type._compose_varint(value)

    assert len(result) == expected_bytes


def test_encode_tiny_int(tiny_int_case):
    decoded, encoded, desc = tiny_int_case
    result = data_type.encode_tiny_int(decoded)

    assert result == encoded


@pytest.mark.parametrize("value", [-1, 256, 1000])
def test_encode_tiny_int_raises_error(value):
    with pytest.raises(SpopEncodeError, match="tiny int must be 0-255"):
        data_type.encode_tiny_int(value)


def test_encode_frame_len(frame_len_case):
    decoded, encoded, desc = frame_len_case
    result = data_type.encode_frame_len(decoded)

    assert result == encoded


@pytest.mark.parametrize("value", [-1, 2**32])
def test_encode_frame_len_raises_error(value):
    with pytest.raises(SpopEncodeError, match="failed to encode frame_len int"):
        data_type.encode_frame_len(value)


def test_encode_int():
    with patch("spoe_forge.spop.encoders.data_types._compose_varint") as mock_varint:
        mock_varint.return_value = b"\x42"
        result = data_type.encode_int(100)
        mock_varint.assert_called_once_with(100)

        assert result == b"\x42"


def test_encode_string(string_case):
    decoded, encoded, desc = string_case
    result = data_type.encode_string(decoded)

    assert result == encoded


def test_encode_string_calls_compose_binary():
    with patch("spoe_forge.spop.encoders.data_types._compose_binary") as mock_binary:
        mock_binary.return_value = b"\x05hello"
        result = data_type.encode_string("hello")
        mock_binary.assert_called_once_with(b"hello")

        assert result == b"\x05hello"


def test_encode_string_accepts_latin1():
    result = data_type.encode_string("héllo")

    assert result == b"\x05h\xe9llo"


def test_encode_string_raises_error_above_latin1():
    with pytest.raises(SpopEncodeError, match="codepoints above 255"):
        data_type.encode_string("h€llo")


def test_compose_binary(binary_case):
    decoded, encoded, desc = binary_case
    result = data_type._compose_binary(decoded)

    assert result == encoded


def test_compose_binary_calls_compose_varint():
    """Test _compose_binary calls _compose_varint for length."""
    with patch("spoe_forge.spop.encoders.data_types._compose_varint") as mock_varint:
        mock_varint.return_value = b"\x05"
        result = data_type._compose_binary(b"hello")
        mock_varint.assert_called_once_with(5)

        assert result == b"\x05hello"


def test_type_data_null():
    result = data_type._type_data(0x00)  # DataType.NULL

    assert result == b"\x00"


def test_type_data_bool_with_flag():
    result = data_type._type_data(0x01, 0x10)  # DataType.BOOL, DataFlag.BOOL_TRUE

    assert result == b"\x11"


def test_type_data_int32():
    result = data_type._type_data(0x02)  # DataType.INT32

    assert result == b"\x02"


def test_encode_dt_null():
    result = data_type.encode_dt_null()

    assert result == b"\x00"


def test_encode_dt_null_calls_type_data():
    with patch("spoe_forge.spop.encoders.data_types._type_data") as mock_type:
        mock_type.return_value = b"\x00"
        result = data_type.encode_dt_null()
        mock_type.assert_called_once()

        assert result == b"\x00"


def test_encode_dt_int32():
    with (
        patch("spoe_forge.spop.encoders.data_types._type_data") as mock_type,
        patch(
            "spoe_forge.spop.encoders.data_types._compose_varint",
        ) as mock_int,
    ):
        mock_type.return_value = b"\x02"
        mock_int.return_value = b"\x2a"
        result = data_type.encode_dt_int32(42)
        mock_int.assert_called_once_with(42)

        assert result == b"\x02\x2a"


def test_encode_dt_uint32():
    with (
        patch("spoe_forge.spop.encoders.data_types._type_data") as mock_type,
        patch(
            "spoe_forge.spop.encoders.data_types._compose_varint",
        ) as mock_int,
    ):
        mock_type.return_value = b"\x03"
        mock_int.return_value = b"\x64"
        result = data_type.encode_dt_uint32(100)
        mock_int.assert_called_once_with(100)

        assert result == b"\x03\x64"


def test_encode_dt_int64():
    with (
        patch("spoe_forge.spop.encoders.data_types._type_data") as mock_type,
        patch(
            "spoe_forge.spop.encoders.data_types._compose_varint",
        ) as mock_int,
    ):
        mock_type.return_value = b"\x04"
        mock_int.return_value = b"\xff\xff\x7f"
        result = data_type.encode_dt_int64(2287)
        mock_int.assert_called_once_with(2287)

        assert result == b"\x04\xff\xff\x7f"


def test_encode_dt_uint64():
    with (
        patch("spoe_forge.spop.encoders.data_types._type_data") as mock_type,
        patch(
            "spoe_forge.spop.encoders.data_types._compose_varint",
        ) as mock_int,
    ):
        mock_type.return_value = b"\x05"  # DataType.UINT64
        mock_int.return_value = b"\x01"
        result = data_type.encode_dt_uint64(1)
        mock_int.assert_called_once_with(1)

        assert result == b"\x05\x01"


def test_encode_dt_bool_true():
    result = data_type.encode_dt_bool(True)

    assert result == b"\x11"


def test_encode_dt_bool_false():
    result = data_type.encode_dt_bool(False)

    assert result == b"\x01"  # DataType.BOOL (no flag)


def test_encode_dt_bool_calls_type_data():
    with patch("spoe_forge.spop.encoders.data_types._type_data") as mock_type:
        mock_type.return_value = b"\x11"
        result = data_type.encode_dt_bool(True)

        assert mock_type.call_count == 1
        assert result == b"\x11"


def test_encode_dt_ipv4(ipv4_case):
    decoded, encoded_no_type, desc = ipv4_case
    result = data_type.encode_dt_ipv4(decoded)

    assert result == b"\x06" + encoded_no_type
    assert len(result) == 5


def test_encode_dt_ipv4_calls_type_data():
    with patch("spoe_forge.spop.encoders.data_types._type_data") as mock_type:
        mock_type.return_value = b"\x06"
        addr = ipaddress.IPv4Address("192.168.1.1")
        result = data_type.encode_dt_ipv4(addr)
        mock_type.assert_called_once()

        assert result == b"\x06" + addr.packed


def test_encode_dt_ipv6(ipv6_case):
    decoded, encoded_no_type, desc = ipv6_case
    result = data_type.encode_dt_ipv6(decoded)

    assert result == b"\x07" + encoded_no_type
    assert len(result) == 17


def test_encode_dt_ipv6_calls_type_data():
    with patch("spoe_forge.spop.encoders.data_types._type_data") as mock_type:
        mock_type.return_value = b"\x07"
        addr = ipaddress.IPv6Address("::1")
        result = data_type.encode_dt_ipv6(addr)
        mock_type.assert_called_once()

        assert result == b"\x07" + addr.packed


def test_encode_dt_binary(binary_case):
    decoded, encoded_no_type, desc = binary_case
    result = data_type.encode_dt_binary(decoded)

    assert result == b"\x09" + encoded_no_type


def test_encode_dt_binary_calls_compose_binary():
    with (
        patch("spoe_forge.spop.encoders.data_types._type_data") as mock_type,
        patch(
            "spoe_forge.spop.encoders.data_types._compose_binary",
        ) as mock_binary,
    ):
        mock_type.return_value = b"\x09"
        mock_binary.return_value = b"\x03abc"
        result = data_type.encode_dt_binary(b"abc")
        mock_binary.assert_called_once_with(b"abc")

        assert result == b"\x09\x03abc"


def test_encode_dt_string(string_case):
    decoded, encoded_no_type, desc = string_case
    result = data_type.encode_dt_string(decoded)

    assert result == b"\x08" + encoded_no_type


def test_encode_dt_string_calls_compose_binary():
    with (
        patch("spoe_forge.spop.encoders.data_types._type_data") as mock_type,
        patch(
            "spoe_forge.spop.encoders.data_types._compose_binary",
        ) as mock_binary,
    ):
        mock_type.return_value = b"\x08"
        mock_binary.return_value = b"\x05hello"
        result = data_type.encode_dt_string("hello")
        mock_binary.assert_called_once_with(b"hello")

        assert result == b"\x08\x05hello"


def test_encode_dt_string_accepts_latin1():
    result = data_type.encode_dt_string("héllo")

    assert result == b"\x08\x05h\xe9llo"


def test_encode_dt_string_raises_error_above_latin1():
    with pytest.raises(SpopEncodeError, match="codepoints above 255"):
        data_type.encode_dt_string("h€llo")


def test_auto_encode_dt_var_null():
    with patch("spoe_forge.spop.encoders.data_types.encode_dt_null") as mock_null:
        mock_null.return_value = b"\x00"
        result = data_type.auto_encode_dt_var(None)
        mock_null.assert_called_once()

        assert result == b"\x00"


def test_auto_encode_dt_var_bool_true():
    with patch("spoe_forge.spop.encoders.data_types.encode_dt_bool") as mock_bool:
        mock_bool.return_value = b"\x11"
        result = data_type.auto_encode_dt_var(True)
        mock_bool.assert_called_once_with(True)

        assert result == b"\x11"


def test_auto_encode_dt_var_bool_false():
    with patch("spoe_forge.spop.encoders.data_types.encode_dt_bool") as mock_bool:
        mock_bool.return_value = b"\x01"
        result = data_type.auto_encode_dt_var(False)
        mock_bool.assert_called_once_with(False)

        assert result == b"\x01"


def test_auto_encode_dt_var_int():
    with patch("spoe_forge.spop.encoders.data_types.encode_dt_int64") as mock_int64:
        mock_int64.return_value = b"\x04\x2a"
        result = data_type.auto_encode_dt_var(42)
        mock_int64.assert_called_once_with(42)

        assert result == b"\x04\x2a"


def test_auto_encode_dt_var_ipv4():
    addr = ipaddress.IPv4Address("192.168.1.1")
    with patch("spoe_forge.spop.encoders.data_types.encode_dt_ipv4") as mock_ipv4:
        mock_ipv4.return_value = b"\x06\xc0\xa8\x01\x01"
        result = data_type.auto_encode_dt_var(addr)
        mock_ipv4.assert_called_once_with(addr)

        assert result == b"\x06\xc0\xa8\x01\x01"


def test_auto_encode_dt_var_ipv6():
    addr = ipaddress.IPv6Address("::1")
    with patch("spoe_forge.spop.encoders.data_types.encode_dt_ipv6") as mock_ipv6:
        mock_ipv6.return_value = b"\x07" + b"\x00" * 15 + b"\x01"
        data_type.auto_encode_dt_var(addr)
        mock_ipv6.assert_called_once_with(addr)


def test_auto_encode_dt_var_bytes():
    with patch("spoe_forge.spop.encoders.data_types.encode_dt_binary") as mock_binary:
        mock_binary.return_value = b"\x09\x03abc"
        result = data_type.auto_encode_dt_var(b"abc")
        mock_binary.assert_called_once_with(b"abc")

        assert result == b"\x09\x03abc"


def test_auto_encode_dt_var_string():
    with patch("spoe_forge.spop.encoders.data_types.encode_dt_string") as mock_string:
        mock_string.return_value = b"\x08\x05hello"
        result = data_type.auto_encode_dt_var("hello")
        mock_string.assert_called_once_with("hello")

        assert result == b"\x08\x05hello"


def test_auto_encode_dt_var_bool_priority_over_int():
    result = data_type.auto_encode_dt_var(True)
    assert result == b"\x11"

    result = data_type.auto_encode_dt_var(False)
    assert result == b"\x01"


def test_auto_encode_dt_var_raises_error_on_unsupported_type():
    with pytest.raises(SpopEncodeError, match="cannot encode unsupported type"):
        data_type.auto_encode_dt_var([1, 2, 3])


def test_auto_encode_dt_var_raises_error_on_dict():
    with pytest.raises(SpopEncodeError, match="cannot encode unsupported type"):
        data_type.auto_encode_dt_var({"key": "value"})


def test_auto_encode_dt_var_raises_error_on_float():
    with pytest.raises(SpopEncodeError, match="cannot encode unsupported type"):
        data_type.auto_encode_dt_var(3.14)
