"""
SPOP Protocol Type Definitions

Dataclasses and type aliases for the more complex SPOE protocol data structures.
"""

import ipaddress
from dataclasses import dataclass
from typing import TypeAlias
from typing import TypeVar

from spoe_forge.spop.constants import ActionScope

# Decoder return type: (decoded_value, new_offset)
_T = TypeVar("_T")
SpoaDec: TypeAlias = tuple[_T, int]

# SPOP data types that can be encoded/decoded
SpoaDataType: TypeAlias = (
    int | bool | ipaddress.IPv4Address | ipaddress.IPv6Address | bytes | str | None
)

# Ordered (name, args) pairs - a NOTIFY frame may legally carry the same
# message name more than once, so this must not be keyed by name
Messages: TypeAlias = list[tuple[str, dict[str, SpoaDataType]]]


@dataclass
class Flags:
    """
    Frame metadata flags.

     Attributes:
         FIN: Frame is final/complete (always True in SPOP 2.0+)
         ABORT: Processing of this frame should be cancelled (rarely if ever set)
    """

    FIN: bool
    ABORT: bool


@dataclass
class MetaData:
    """
    Frame metadata present in all SPOP frames.

    Attributes:
        flags: Frame flags (FIN, ABORT)
        stream_id: HAProxy stream identifier
        frame_id: Frame sequence number within the stream
    """

    flags: Flags
    stream_id: int
    frame_id: int


@dataclass
class SetVarAction:
    """
    Action to set a variable in HAProxy.

    Attributes:
        scope: Where to store the variable (SESSION, TRANSACTION, REQUEST, RESPONSE)
        name: Variable name (will be prefixed with scope in HAProxy, e.g., sess.user_authenticated)
        value: Value to set (int, str, bool, bytes, IPv4Address, IPv6Address).
               str values must be latin-1-encodable (codepoints <= 255); pass
               arbitrary text as UTF-8 bytes instead.
    """

    scope: ActionScope
    name: str
    value: SpoaDataType


@dataclass
class UnsetVarAction:
    """
    Action to remove a variable from HAProxy.

    Attributes:
        scope: Where the variable is stored
        name: Variable name to remove
    """

    scope: ActionScope
    name: str


# Type alias for any action
Action: TypeAlias = SetVarAction | UnsetVarAction
