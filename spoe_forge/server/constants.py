from enum import IntEnum

SPOE_VERSION = "2.0"
"""Hardcoded to the version of SPOP we built around"""

SPOE_CAPABILITIES = ["pipelining"]
"""Pipelining is the only capability available in 2.0"""

DEFAULT_MAX_FRAME_SIZE = 1024 * 4
"""4kb max frame size - set to a comfortably low value"""


class DisconnectCode(IntEnum):
    # Predefined by HAProxy Protocol
    NORMAL = 0
    IO_ERROR = 1
    TIMEOUT = 2
    FRAME_TOO_BIG = 3
    INVALID_FRAME_RECEIVED = 4
    VERSION_NOT_FOUND = 5
    MAX_FRAME_SIZE_NOT_FOUND = 6
    CAPABILITY_NOT_FOUND = 7
    UNSUPPORTED_VERSION = 8
    MAX_FRAME_SIZE_OUT_OF_RANGE = 9
    FRAGMENTATION_NOT_SUPPORTED = 10
    INVALID_INTERLACED_FRAME = 11
    FRAME_ID_NOT_FOUND = 12
    RESOURCE_ALLOCATION_ERROR = 13
    UNKNOWN_ERROR = 99

    # Custom Error Codes
    SERVER_INCOMPATIBLE = 101
    PROTOCOL_ERROR = 102
