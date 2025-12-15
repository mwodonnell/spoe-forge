import ctypes
import ipaddress
import logging
import struct

from spoe_forge.spop.constants import DataFlag
from spoe_forge.spop.constants import DataType
from spoe_forge.spop.exception import SpopEncodeError
from spoe_forge.spop.spop_types import SpoaDataType

logger = logging.getLogger(__name__)


async def _compose_varint(val: int) -> bytes:
    """
    Compose Varint for SPOA protocol.

    SPOP encodes integers based on size:
          0  <= X < 240        : 1 byte  (7.875 bits)  [ XXXX XXXX ]
         240 <= X < 2288       : 2 bytes (11 bits)     [ 1111 XXXX ] [ 0XXX XXXX ]
        2288 <= X < 264432     : 3 bytes (18 bits)     [ 1111 XXXX ] [ 1XXX XXXX ]   [ 0XXX XXXX ]
      264432 <= X < 33818864   : 4 bytes (25 bits)     [ 1111 XXXX ] [ 1XXX XXXX ]*2 [ 0XXX XXXX ]
    33818864 <= X < 4328786160 : 5 bytes (32 bits)     [ 1111 XXXX ] [ 1XXX XXXX ]*3 [ 0XXX XXXX ]
    ... pattern continues for larger values (up to 10 bytes for full 64-bit support)

    The pattern continues: each additional byte adds 7 bits of data.
    10 bytes total (4 + 7*9 = 67 bits) can encode the full uint64 range.

    :param int val: Integer value to encode
    :return: Encoded bytes
    """
    if val < 0:
        raise SpopEncodeError(f"cannot encode negative number as varint: {val}")

    if val < 240:
        return bytes([val])

    out = bytearray()
    out.append((val | 0xF0) & 0xFF)

    val = (val - 240) >> 4
    while val >= 128:
        out.append((val | 0x80) & 0xFF)
        val = (val - 128) >> 7

    out.append(val)
    return bytes(out)


async def _compose_binary(val: bytes) -> bytes:
    """
    Encode binary data with varint length prefix.

    :param bytes val: Binary data to encode
    :return: Encoded bytes with length prefix
    """
    length_var = await _compose_varint(len(val))
    return length_var + val


async def _type_data(data_type: DataType, flags: int = 0x00) -> bytes:
    """
    Create TYPE + FLAGS byte for SPOA protocol.

    Booleans encode their value within the flags.

    :param DataType data_type: Data type to encode
    :param int flags: Flags to encode (default 0x00) - should already be positioned in high nibble
    :return: Encoded TYPE + FLAGS byte
    """
    return (flags | data_type).to_bytes(1, byteorder="big")


async def encode_tiny_int(val: int) -> bytes:
    """
    Encode 1-byte integer for SPOA protocol.

    :param int val: Integer value to encode (0-255)
    :return: Encoded bytes
    """
    if not 0 <= val <= 255:
        raise SpopEncodeError(f"tiny int must be 0-255, got {val}")

    return val.to_bytes(length=1, byteorder="big")


async def encode_frame_len(frame_len: int) -> bytes:
    """
    Encode frame length as 4-byte big-endian integer.

    :param int frame_len: Frame length in bytes
    :return: Encoded bytes
    """
    try:
        return struct.pack("!I", frame_len)
    except struct.error:
        raise SpopEncodeError(
            "failed to encode frame_len int",
        )


async def encode_int(val: int) -> bytes:
    """
    Encode integer as varint for SPOA protocol.

    :param int val: Integer value to encode
    :return: Encoded bytes
    """
    return await _compose_varint(val)


async def encode_string(val: str) -> bytes:
    """
    Encode string as ASCII with varint length prefix.

    :param str val: String to encode
    :return: Encoded bytes
    """
    try:
        return await _compose_binary(val.encode("ascii"))
    except UnicodeEncodeError:
        raise SpopEncodeError(
            f"cannot encode non-ASCII string to SPOP: {val!r}",
        )


async def encode_dt_null() -> bytes:
    """
    Encode NULL data type for SPOA protocol.

    NULLs are represented by a single type byte with no data.

    :return: Encoded bytes
    """
    return await _type_data(DataType.NULL)


async def encode_dt_int32(val: int) -> bytes:
    """
    Encode INT32 with type prefix for SPOA protocol.

    :param int val: Integer value to encode
    :return: Encoded bytes
    """
    # Convert signed to unsigned representation for varint encoding
    try:
        unsigned_val = ctypes.c_uint32(val).value
    except ValueError:
        raise SpopEncodeError(
            f"cannot encode INT32 value to SPOP: {val!r}",
        )
    return await _type_data(DataType.INT32) + await _compose_varint(unsigned_val)


async def encode_dt_int64(val: int) -> bytes:
    """
    Encode INT64 with type prefix for SPOA protocol.

    :param int val: Integer value to encode
    :return: Encoded bytes
    """
    # Convert signed to unsigned representation for varint encoding
    try:
        unsigned_val = ctypes.c_uint64(val).value
    except ValueError:
        raise SpopEncodeError(
            f"cannot encode INT64 value to SPOP: {val!r}",
        )
    return await _type_data(DataType.INT64) + await _compose_varint(unsigned_val)


async def encode_dt_uint32(val: int) -> bytes:
    """
    Encode UINT32 with type prefix for SPOA protocol.

    :param int val: Integer value to encode
    :return: Encoded bytes
    """
    # Ensure value fits in uint32
    try:
        unsigned_val = ctypes.c_uint32(val).value
    except ValueError:
        raise SpopEncodeError(
            f"cannot encode UINT32 value to SPOP: {val!r}",
        )
    return await _type_data(DataType.UINT32) + await _compose_varint(unsigned_val)


async def encode_dt_uint64(val: int) -> bytes:
    """
    Encode UINT64 with type prefix for SPOA protocol.

    :param int val: Integer value to encode
    :return: Encoded bytes
    """
    # Ensure value fits in uint64
    try:
        unsigned_val = ctypes.c_uint64(val).value
    except ValueError:
        raise SpopEncodeError(
            f"cannot encode UINT64 value to SPOP: {val!r}",
        )
    return await _type_data(DataType.UINT64) + await _compose_varint(unsigned_val)


async def encode_dt_bool(val: bool) -> bytes:
    """
    Encode boolean with type prefix for SPOA protocol.

    Boolean value is encoded in the FLAGS portion of the type byte.

    :param bool val: Boolean value to encode
    :return: Encoded bytes
    """
    flag = DataFlag.BOOL_TRUE if val else DataFlag.BOOL_FALSE
    return await _type_data(DataType.BOOL, flag)


async def encode_dt_ipv4(val: ipaddress.IPv4Address) -> bytes:
    """
    Encode IPv4 address with type prefix for SPOA protocol.

    :param ipaddress.IPv4Address val: IPv4 address to encode
    :return: Encoded bytes
    """
    return await _type_data(DataType.IPV4) + val.packed


async def encode_dt_ipv6(val: ipaddress.IPv6Address) -> bytes:
    """
    Encode IPv6 address with type prefix for SPOA protocol.

    :param ipaddress.IPv6Address val: IPv6 address to encode
    :return: Encoded bytes
    """
    return await _type_data(DataType.IPV6) + val.packed


async def encode_dt_binary(val: bytes) -> bytes:
    """
    Encode binary data with type prefix for SPOA protocol.

    :param bytes val: Binary data to encode
    :return: Encoded bytes
    """
    return await _type_data(DataType.BINARY) + await _compose_binary(val)


async def encode_dt_string(val: str) -> bytes:
    """
    Encode string with type prefix for SPOA protocol.

    Strings must be ASCII-encodable.

    :param str val: String to encode
    :return: Encoded bytes
    """
    try:
        return await _type_data(DataType.STRING) + await _compose_binary(
            val.encode("ascii")
        )
    except UnicodeEncodeError:
        raise SpopEncodeError(
            f"cannot encode non-ASCII string to SPOP: {val!r}",
        )


async def auto_encode_dt_var(val: SpoaDataType) -> bytes:
    """
    Automatically detect type and encode with appropriate type prefix.

    All Python ints are encoded as INT64.

    :param SpoaDataType val: Value to encode
    :return: Encoded bytes
    """
    logger.debug(f"Auto-encoding value: {type(val).__name__} = {val!r}")

    if val is None:
        result = await encode_dt_null()

    elif isinstance(val, bool):
        # Check bool before int since bool is a subclass of int in Python
        result = await encode_dt_bool(val)

    elif isinstance(val, int):
        result = await encode_dt_int64(val)

    elif isinstance(val, ipaddress.IPv4Address):
        result = await encode_dt_ipv4(val)

    elif isinstance(val, ipaddress.IPv6Address):
        result = await encode_dt_ipv6(val)

    elif isinstance(val, bytes):
        result = await encode_dt_binary(val)

    elif isinstance(val, str):
        result = await encode_dt_string(val)

    else:
        raise SpopEncodeError(
            f"cannot encode unsupported type {type(val)} ({val})",
        )

    logger.debug(f"Encoded as {len(result)} bytes")
    return result
