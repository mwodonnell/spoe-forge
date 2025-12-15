import logging

from spoe_forge.spop.constants import ActionType
from spoe_forge.spop.constants import ActionScope
from spoe_forge.spop.constants import FrameFlag
from spoe_forge.spop.decoders.data_types import auto_decode_var
from spoe_forge.spop.decoders.data_types import decode_int64
from spoe_forge.spop.decoders.data_types import decode_string
from spoe_forge.spop.decoders.data_types import decode_tiny_int
from spoe_forge.spop.exception import SpopDecodeError
from spoe_forge.spop.spop_types import Action
from spoe_forge.spop.spop_types import SetVarAction
from spoe_forge.spop.spop_types import UnsetVarAction
from spoe_forge.spop.spop_types import Flags
from spoe_forge.spop.spop_types import MetaData
from spoe_forge.spop.spop_types import SpoaDataType
from spoe_forge.spop.spop_types import SpoaDec

logger = logging.getLogger(__name__)


async def _parse_kv_pair(buf: bytes, offset=0) -> tuple[str, SpoaDataType, int]:
    """
    Decode key-value pair from SPOA protocol.

    :param bytes buf: SPOP byte stream to consume from
    :param int offset: Offset to start reading from
    :return: Tuple of (key, value, adjusted offset)
    """
    key, offset = await decode_string(buf, offset)
    val, offset = await auto_decode_var(buf, offset)

    return key, val, offset


async def decode_metadata(buf: bytes, offset=0) -> SpoaDec[MetaData]:
    """
    Decode frame metadata from SPOA protocol.

    METADATA: <FLAGS:4 bytes> <STREAM-ID:varint> <FRAME-ID:varint>

    :param bytes buf: SPOP byte stream to consume from
    :param int offset: Offset to start reading from
    :return: Tuple of MetaData object and adjusted offset
    """
    end = offset + 4
    if end >= len(buf):
        raise SpopDecodeError(
            "unexpected end of stream decoding metadata",
        )
    flags_buf = buf[offset:end]

    # HAProxy only sends 2 flags which are in the first byte of the
    # 4 byte payload, we ignore the other 3 bytes
    flags = Flags(
        FIN=flags_buf[-1] & FrameFlag.FIN == FrameFlag.FIN,
        ABORT=flags_buf[-1] & FrameFlag.ABORT == FrameFlag.ABORT,
    )

    offset = end
    try:
        stream_id, offset = await decode_int64(buf, offset)
    except SpopDecodeError as e:
        raise SpopDecodeError(f"error decoding stream_id in metadata: {e}")

    try:
        frame_id, offset = await decode_int64(buf, offset)
    except SpopDecodeError as e:
        raise SpopDecodeError(f"error decoding frame_id in metadata: {e}")

    return MetaData(
        flags=flags,
        stream_id=stream_id,
        frame_id=frame_id,
    ), offset


async def decode_kv_list(
    buf: bytes, offset: int = 0, end: int = 0
) -> SpoaDec[dict[str, SpoaDataType]]:
    """
    Decode key-value list from SPOA protocol.

    KV-LIST: [<KV-NAME> <KV-VALUE> <...> ]
      KV-NAME:  <STRING>
      KV-VALUE: <TYPED-DATA>

    :param bytes buf: SPOP byte stream to consume from
    :param int offset: Offset to start reading from
    :param int end: Expected end position (usually frame_len)
    :return: Tuple of decoded key-value map and adjusted offset
    """
    logger.debug(f"Decoding KV list: {end - offset} bytes to process")

    payload = {}
    while offset < end:
        key, val, offset = await _parse_kv_pair(buf, offset)
        payload[key] = val

    logger.debug(f"Decoded KV list: {len(payload)} pairs")
    return payload, offset


async def decode_list_of_messages(
    buf: bytes, offset: int = 0, end: int = 0
) -> SpoaDec[dict[str, dict[str, SpoaDataType]]]:
    """
    Decode message list from SPOA protocol.

    LIST-OF-MESSAGES: [ <MESSAGE-NAME> <NB-ARGS:1 byte> <KV-LIST> ... ]
        MESSAGE-NAME: <STRING>

    :param bytes buf: SPOP byte stream to consume from
    :param int offset: Offset to start reading from
    :param int end: Expected end position (usually frame_len)
    :return: Tuple of messages with their arguments and adjusted offset
    :raises SpopDecodeError: If duplicate argument found in message
    """
    logger.debug(f"Decoding message list: {end - offset} bytes to process")

    payload = {}
    while offset < end:
        message, offset = await decode_string(buf, offset)
        num_args, offset = await decode_tiny_int(buf, offset)

        args = {}
        for _ in range(num_args):
            k, v, offset = await _parse_kv_pair(buf, offset)

            if k in args:
                raise SpopDecodeError(
                    f"unexpected duplicate arg {k} in message {message}",
                )

            args[k] = v

        payload[message] = args

    logger.debug(f"Decoded {len(payload)} messages")
    return payload, offset


async def decode_list_of_actions(
    buf: bytes, offset: int = 0, end: int = 0
) -> SpoaDec[list[Action]]:
    """
    Decode action list from SPOA protocol.

    LIST-OF-ACTIONS: [ <ACTION-TYPE:1 byte> <NB-ARGS:1 byte> <ACTION-ARGS> ... ]
        ACTION-ARGS: [ <TYPED-DATA>... ]

    :param bytes buf: SPOP byte stream to consume from
    :param int offset: Offset to start reading from
    :param int end: Expected end position (usually frame_len)
    :return: Tuple of decoded actions list and adjusted offset
    :raises SpopDecodeError: If invalid action type or scope encountered
    """
    logger.debug(f"Decoding action list: {end - offset} bytes to process")

    if len(buf) == end + 1:
        # Action lists can be empty - we don't throw an error here, instead return an empty list
        return [], offset

    actions = []
    while offset < end:
        try:
            action = ActionType(buf[offset])
        except ValueError:
            raise SpopDecodeError(f"invalid action type: {buf[offset]}")
        offset += 2  # Skip NB-ARGS byte

        try:
            scope = ActionScope(buf[offset])
        except ValueError:
            raise SpopDecodeError(f"invalid action scope: {buf[offset]}")
        offset += 1

        if action == ActionType.SET_VAR:
            arg, val, offset = await _parse_kv_pair(buf, offset)
            actions.append(
                SetVarAction(
                    scope=scope,
                    name=arg,
                    value=val,
                )
            )

        elif action == ActionType.UNSET_VAR:
            arg, offset = await decode_string(buf, offset)
            actions.append(
                UnsetVarAction(
                    scope=scope,
                    name=arg,
                )
            )

        else:
            raise SpopDecodeError(
                f"unknown action {action}",
            )

    logger.debug(f"Decoded {len(actions)} actions")

    return actions, offset
