"""
SPOP Protocol Constants

Enums and constants for the SPOE (Stream Processing Offload Engine) protocol.

References:
    SPOE Protocol Specification:
    https://raw.githubusercontent.com/haproxy/haproxy/refs/tags/v3.2.0/doc/SPOE.txt
"""

from enum import IntEnum
from enum import IntFlag
from typing import Final

# We support the 2.0 SPOP Version for now
SPOP_PROTOCOL_VERSION_SUPPORTED: Final[str] = "2.0"
SPOP_PROTOCOL_CAPABILITIES: Final[str] = ""


class DataFlag(IntFlag):
    """
    Flags used in the BOOL data type encoding.
    """

    BOOL_TRUE = 0x10
    BOOL_FALSE = 0x00


class DataTypeMask(IntFlag):
    """
    Bit masks for extracting type and flags from the type byte.
    """

    TYPE = 0x0F
    FLAG = 0xF0


class FrameFlag(IntFlag):
    """
    Frame metadata flags.
    """

    FIN = 0x01
    ABORT = 0x02


class DataType(IntEnum):
    """
    SPOP data type identifiers.

    Each value represents a different data type encoding in the SPOE protocol.
    """

    NULL = 0
    BOOL = 1
    INT32 = 2
    UINT32 = 3
    INT64 = 4
    UINT64 = 5
    IPV4 = 6
    IPV6 = 7
    STRING = 8
    BINARY = 9


class FrameType(IntEnum):
    """
    SPOP frame type identifiers.

    Frame types 1-3 are from HAProxy to Agent.
    Frame types 101-103 are from Agent to HAProxy.
    """

    UNSET = 0
    HAPROXY_HELLO = 1
    HAPROXY_DISCONNECT = 2
    NOTIFY = 3
    AGENT_HELLO = 101
    AGENT_DISCONNECT = 102
    ACK = 103


class ActionType(IntEnum):
    """
    Action types that can be sent in ACK frames.
    """

    SET_VAR = 1
    UNSET_VAR = 2


class ActionNBArgs(IntEnum):
    """
    Number of arguments required for each action type.
    """

    SET_VAR = 3
    UNSET_VAR = 2


class ActionScope(IntEnum):
    """
    Variable scopes in HAProxy.

    Determines the lifetime and visibility of variables set via actions.
    """

    PROCESS = 0
    SESSION = 1
    TRANSACTION = 2
    REQUEST = 3
    RESPONSE = 4
