import ctypes
import ipaddress
import logging
import struct

from spoe_forge.spop.constants import DataFlag
from spoe_forge.spop.constants import DataType
from spoe_forge.spop.constants import DataTypeMask
from spoe_forge.spop.exception import SpopDecodeError
from spoe_forge.spop.spop_types import SpoaDataType
from spoe_forge.spop.spop_types import SpoaDec

logger = logging.getLogger(__name__)


async def _parse_varint(buf: bytes, offset=0) -> SpoaDec[int]:
    """
    Decode Varint from SPOA protocol.

    SPOP encodes integers based on size:
          0  <= X < 240        : 1 byte  (7.875 bits)  [ XXXX XXXX ]
         240 <= X < 2288       : 2 bytes (11 bits)     [ 1111 XXXX ] [ 0XXX XXXX ]
        2288 <= X < 264432     : 3 bytes (18 bits)     [ 1111 XXXX ] [ 1XXX XXXX ]   [ 0XXX XXXX ]
      264432 <= X < 33818864   : 4 bytes (25 bits)     [ 1111 XXXX ] [ 1XXX XXXX ]*2 [ 0XXX XXXX ]
    33818864 <= X < 4328786160 : 5 bytes (32 bits)     [ 1111 XXXX ] [ 1XXX XXXX ]*3 [ 0XXX XXXX ]

    Reads bytes until it hits a stop bit of 0x80 == 0

    :param bytes buf: SPOP byte stream to consume from
    :param int offset: offset to start reading from
    :return: Tuple of the parsed integer, and the adjusted offset
    """
    if offset >= len(buf):
        raise SpopDecodeError(
            "unexpected end of stream decoding varint",
        )

    first_byte = buf[offset]
    if first_byte < 240:
        return first_byte, offset + 1

    value = first_byte
    shift = 4

    while True:
        offset += 1
        if offset >= len(buf):
            raise SpopDecodeError(
                "unexpected end of stream decoding varint",
            )

        next_byte = buf[offset]
        value += next_byte << shift

        if next_byte < 128:
            return value, offset + 1

        shift += 7


async def decode_tiny_int(buf: bytes, offset=0) -> SpoaDec[int]:
    """
    Decode 1 byte integer from SPOA protocol.

    :param buf: SPOP byte stream to consume from
    :param offset: offset to start reading from
    :return: Tuple of the parsed integer, and the adjusted offset
    """

    if offset >= len(buf):
        raise SpopDecodeError(
            "unexpected end of stream decoding tiny int",
        )

    # Python automatically interprets this as an int from bytes in Big Endian
    return buf[offset], offset + 1


async def decode_frame_len(len_buf: bytes) -> int:
    try:
        (frame_len,) = struct.unpack("!I", len_buf)
    except struct.error:
        raise SpopDecodeError("unexpected error decoding frame length")

    return frame_len


async def decode_int32(buf: bytes, offset=0) -> SpoaDec[int]:
    """
    Decode INT32 from SPOA protocol

    :param buf: SPOP byte stream to consume from
    :param offset: offset to start reading from
    :return: Tuple of the parsed integer, and the adjusted offset
    """
    val, offset = await _parse_varint(buf, offset)
    return ctypes.c_int32(val).value, offset


async def decode_int64(buf: bytes, offset=0) -> SpoaDec[int]:
    """
    Decode INT64 from SPOA protocol

    :param buf: SPOP byte stream to consume from
    :param offset: offset to start reading from
    :return: Tuple of the parsed integer, and the adjusted offset
    """
    val, offset = await _parse_varint(buf, offset)
    return ctypes.c_int64(val).value, offset


async def decode_uint32(buf: bytes, offset=0) -> SpoaDec[int]:
    """
    Decode UINT32 from SPOA protocol

    :param buf: SPOP byte stream to consume from
    :param offset: offset to start reading from
    :return: Tuple of the parsed integer, and the adjusted offset
    """
    val, offset = await _parse_varint(buf, offset)
    return ctypes.c_uint32(val).value, offset


async def decode_uint64(buf: bytes, offset=0) -> SpoaDec[int]:
    """
    Decode UINT64 from SPOA protocol

    :param buf: SPOP byte stream to consume from
    :param offset: offset to start reading from
    :return: Tuple of the parsed integer, and the adjusted offset
    """
    val, offset = await _parse_varint(buf, offset)
    return ctypes.c_uint64(val).value, offset


async def decode_bool(buf: bytes, offset=0) -> SpoaDec[bool]:
    """
    Decode boolean from SPOA protocol

    Bools are a bit odd as they utilize the rarely used <FLAG> within the type definition rather than sending any
    extra bytes. We actually read the same TYPE byte used to determine the data type to also determine the bools
    value

    :param buf: SPOP byte stream to consume from
    :param offset: offset to start reading from
    :return: Tuple of the parsed boolean, and the adjusted offset
    """
    if offset >= len(buf):
        raise SpopDecodeError(
            "unexpected end of stream decoding boolean",
        )

    return buf[offset] & DataTypeMask.FLAG == DataFlag.BOOL_TRUE, offset + 1


async def decode_ipv4(buf: bytes, offset=0) -> SpoaDec[ipaddress.IPv4Address]:
    """
    Decode IPv4 from SPOA protocol. IPv4 always takes 4 bytes

    :param bytes buf: SPOP byte stream to consume from
    :param int offset: offset to start reading from
    :return: Tuple of the IPv4 as a string, the adjusted offset
    """
    end = offset + 4
    if len(buf) < end:
        raise SpopDecodeError(
            "unexpected end of stream decoding ipv4",
        )

    return ipaddress.IPv4Address(buf[offset:end]), end


async def decode_ipv6(buf: bytes, offset=0) -> SpoaDec[ipaddress.IPv6Address]:
    """
    Decode IPv6 from SPOA protocol. IPv6 always takes 16 bytes

    :param bytes buf: SPOP byte stream to consume from
    :param int offset: offset to start reading from
    :return: Tuple of the IPv6 as a string, and the adjusted offset
    """
    end = offset + 16
    if len(buf) < end:
        raise SpopDecodeError(
            "unexpected end of stream decoding ipv6",
        )

    return ipaddress.IPv6Address(buf[offset:end]), end


async def decode_binary(buf: bytes, offset=0) -> SpoaDec[bytes]:
    """
    Decode binary from SPOA protocol

    :param buf: SPOP byte stream to consume from
    :param offset: offset to start reading from
    :return: Tuple of the parsed bytes and the adjusted offset
    """
    bin_len, offset = await _parse_varint(buf, offset)
    end = offset + bin_len

    if len(buf) < end:
        raise SpopDecodeError(
            "unexpected end of stream decoding binary",
        )

    return buf[offset:end], end


async def decode_string(buf: bytes, offset=0) -> SpoaDec[str]:
    """
    Decode string from SPOA protocol

    No indication of how strings are encoded - using ASCII until we see odd behavior

    :param buf: SPOP byte stream to consume from
    :param offset: offset to start reading from
    :return: Tuple of the parsed string, and the adjusted offset
    """
    _bytes, offset = await decode_binary(buf, offset)
    try:
        return _bytes.decode("ascii"), offset
    except UnicodeDecodeError as e:
        raise SpopDecodeError(f"invalid ASCII string in SPOP stream: {e}")


async def auto_decode_var(buf: bytes, offset=0) -> SpoaDec[SpoaDataType]:
    """
    Decode var from SPOA protocol

    :param buf: SPOP byte stream to consume from
    :param offset: offset to start reading from
    :return: Tuple of the decoded var, and the adjusted offset
    """
    if len(buf) < offset + 1:
        raise SpopDecodeError("unexpected end of stream reading data type")

    val_type = buf[offset] & DataTypeMask.TYPE
    offset += 1

    try:
        val_type = DataType(val_type)
    except ValueError:
        raise SpopDecodeError(f"unknown data type {val_type}")

    logger.debug(f"Decoding typed var: type={DataType(val_type).name}")

    if val_type == DataType.NULL:
        val = None

    elif val_type == DataType.BOOL:
        offset -= 1  # Bools are derived from the same offset as the datatype byte
        val, offset = await decode_bool(buf, offset)

    elif val_type == DataType.INT32:
        val, offset = await decode_int32(buf, offset)

    elif val_type == DataType.UINT32:
        val, offset = await decode_uint32(buf, offset)

    elif val_type == DataType.INT64:
        val, offset = await decode_int64(buf, offset)

    elif val_type == DataType.UINT64:
        val, offset = await decode_uint64(buf, offset)

    elif val_type == DataType.IPV4:
        val, offset = await decode_ipv4(buf, offset)

    elif val_type == DataType.IPV6:
        val, offset = await decode_ipv6(buf, offset)

    elif val_type == DataType.STRING:
        val, offset = await decode_string(buf, offset)

    elif val_type == DataType.BINARY:
        val, offset = await decode_binary(buf, offset)

    else:
        raise SpopDecodeError(f"unknown data type {val_type}")

    logger.debug(f"Decoded {DataType(val_type).name}: {val!r}")
    return val, offset
