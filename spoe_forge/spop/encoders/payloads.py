import logging
from functools import singledispatch

from spoe_forge.spop.constants import ActionType
from spoe_forge.spop.constants import ActionNBArgs
from spoe_forge.spop.constants import FrameFlag
from spoe_forge.spop.encoders.data_types import auto_encode_dt_var
from spoe_forge.spop.encoders.data_types import encode_int
from spoe_forge.spop.encoders.data_types import encode_string
from spoe_forge.spop.encoders.data_types import encode_tiny_int
from spoe_forge.spop.exception import SpopEncodeError
from spoe_forge.spop.spop_types import (
    MetaData,
    Action,
    SetVarAction,
    UnsetVarAction,
    Messages,
)
from spoe_forge.spop.spop_types import SpoaDataType

logger = logging.getLogger(__name__)


async def _compose_kv_pair(k: str, v: SpoaDataType) -> bytes:
    """
    Encode key-value pair for SPOA protocol.

    :param str k: Key string
    :param SpoaDataType v: Value to encode
    :return: Encoded bytes
    """
    out = bytearray()

    k_encoded = await encode_string(k)
    out.extend(k_encoded)

    v_encoded = await auto_encode_dt_var(v)
    out.extend(v_encoded)

    return bytes(out)


@singledispatch
async def _compose_action(action) -> bytes:
    """
    Encode SPOP action using singledispatch pattern.

    Base handler catches unknown action types and raises SpopEncodeError.
    Registered handlers:
        SetVarAction   -> _compose_set_action
        UnsetVarAction -> _compose_unset_action

    :param Action action: Action to encode
    :return: Encoded bytes
    :raises SpopEncodeError: If action type is not recognized
    """
    raise SpopEncodeError(
        f"Unexpected Action while encoding: {action.__class__.__name__}",
    )


@_compose_action.register
async def _compose_set_action(action: SetVarAction) -> bytes:
    """
    Encode SET_VAR action for SPOA protocol.

    :param SetVarAction action: SetVarAction to encode
    :return: Encoded bytes
    """
    out = bytearray()
    out.append(ActionType.SET_VAR)
    out.append(ActionNBArgs.SET_VAR)
    out.append(action.scope)
    out.extend(await encode_string(action.name))
    out.extend(await auto_encode_dt_var(action.value))

    return bytes(out)


@_compose_action.register
async def _compose_unset_action(action: UnsetVarAction) -> bytes:
    """
    Encode UNSET_VAR action for SPOA protocol.

    :param UnsetVarAction action: UnsetVarAction to encode
    :return: Encoded bytes
    """
    out = bytearray()
    out.append(ActionType.UNSET_VAR)
    out.append(ActionNBArgs.UNSET_VAR)
    out.append(action.scope)
    out.extend(await encode_string(action.name))

    return bytes(out)


async def encode_kv_list(payload: dict[str, SpoaDataType]) -> bytes:
    """
    Encode key-value list for SPOA protocol.

    KV-LIST: [<KV-NAME> <KV-VALUE> <...> ]
      KV-NAME:  <STRING>
      KV-VALUE: <TYPED-DATA>

    :param dict[str, SpoaDataType] payload: Key-value pairs to encode
    :return: Encoded bytes
    """
    logger.debug(f"Encoding KV list: {len(payload)} pairs")

    out = bytearray()
    for k, v in payload.items():
        out.extend(await _compose_kv_pair(k, v))

    logger.debug(f"Encoded KV list: {len(out)} bytes")
    return bytes(out)


async def encode_message_list(messages: Messages) -> bytes:
    """
    Encode message list for SPOA protocol.

    LIST-OF-MESSAGES: [ <MESSAGE-NAME> <NB-ARGS:1 byte> <KV-LIST> ... ]
        MESSAGE-NAME: <STRING>
        KV-LIST: [<KV-NAME> <KV-VALUE> <...> ]
            KV-NAME:  <STRING>
            KV-VALUE: <TYPED-DATA>

    :param dict[str, dict[str, SpoaDataType]] messages: Messages with arguments
    :return: Encoded bytes
    :raises SpopEncodeError: If message has more than 255 arguments
    """
    logger.debug(f"Encoding {len(messages)} messages")

    out = bytearray()
    for message, args in messages.items():
        if len(args) > 255:
            raise SpopEncodeError(
                f"message '{message}' has too many args: {len(args)} (max 255)"
            )

        out.extend(await encode_string(message))
        out.extend(await encode_tiny_int(len(args)))

        for k, v in args.items():
            out.extend(await _compose_kv_pair(k, v))

    logger.debug(f"Encoded message list: {len(out)} bytes")
    return bytes(out)


async def encode_action_list(actions: list[Action]) -> bytes:
    """
    Encode action list for SPOA protocol.

    LIST-OF-ACTIONS: [ <ACTION-TYPE:1 byte> <NB-ARGS:1 byte> <ACTION-ARGS> ... ]
        ACTION-ARGS: [ <TYPED-DATA>... ]

    See SPOE Docs section 3.4 for more details on supported actions:
    https://raw.githubusercontent.com/haproxy/haproxy/refs/tags/v3.2.0/doc/SPOE.txt

    :param list[Action] actions: List of actions to encode
    :return: Encoded bytes
    """
    out = bytearray()
    for action in actions:
        out.extend(await _compose_action(action))

    return bytes(out)


async def encode_metadata(metadata: MetaData) -> bytes:
    """
    Encode frame metadata for SPOA protocol.

    METADATA: <FLAGS:4 bytes> <STREAM-ID:varint> <FRAME-ID:varint>

    :param MetaData metadata: Metadata object to encode
    :return: Encoded bytes
    """
    out = bytearray()

    flags = bytearray(int.to_bytes(0, length=4, byteorder="big"))
    # FIN/ABORT flags live in the least significant byte. We will expand as needed if SPOP ever
    # defines more flags in the protocol.
    if metadata.flags.FIN:
        flags[-1] |= FrameFlag.FIN

    if metadata.flags.ABORT:
        flags[-1] |= FrameFlag.ABORT

    out.extend(flags)

    out.extend(await encode_int(metadata.stream_id))
    out.extend(await encode_int(metadata.frame_id))

    return bytes(out)
