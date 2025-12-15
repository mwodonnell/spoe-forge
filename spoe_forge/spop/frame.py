import logging
from abc import ABC
from abc import abstractmethod
from asyncio import IncompleteReadError
from asyncio import StreamReader
from typing import Callable
from typing import ClassVar
from typing import Type

from spoe_forge.exception import SpoeForgeError
from spoe_forge.spop.constants import FrameType
from spoe_forge.spop.decoders.data_types import decode_frame_len
from spoe_forge.spop.decoders.payloads import decode_kv_list
from spoe_forge.spop.decoders.payloads import decode_list_of_actions
from spoe_forge.spop.decoders.payloads import decode_list_of_messages
from spoe_forge.spop.decoders.payloads import decode_metadata
from spoe_forge.spop.encoders.data_types import encode_frame_len
from spoe_forge.spop.encoders.data_types import encode_tiny_int
from spoe_forge.spop.encoders.payloads import encode_action_list
from spoe_forge.spop.encoders.payloads import encode_kv_list
from spoe_forge.spop.encoders.payloads import encode_message_list
from spoe_forge.spop.encoders.payloads import encode_metadata
from spoe_forge.spop.exception import SpopDecodeError
from spoe_forge.spop.exception import SpopEncodeError
from spoe_forge.spop.exception import SpopEOFError
from spoe_forge.spop.spop_types import Action, Messages
from spoe_forge.spop.spop_types import Flags
from spoe_forge.spop.spop_types import MetaData
from spoe_forge.spop.spop_types import SpoaDec

logger = logging.getLogger(__name__)


class Frame(ABC):
    """
    Base Frame class.

    Handles common Frame interactions like storing the Frame Type and Frame Metadata.

    Enforces all frames to implement an Encoder/Decode/Construct for its payload. While this is not strictly
    necessary, it makes things more predictable and cleaner for testing
    """

    frame_type: FrameType
    metadata: MetaData

    _registry: ClassVar[dict[FrameType, Type["Frame"]]] = {}

    def __init__(self, frame_type: FrameType, metadata: MetaData):
        """
        Initialize frame with type and metadata.

        :param FrameType frame_type: Type of frame
        :param MetaData metadata: Frame metadata (flags, stream_id, frame_id)
        """
        self.frame_type = frame_type
        self.metadata = metadata

    @classmethod
    def register(cls, *frame_types: FrameType) -> Callable:
        """
        Register frame type(s) with a Frame subclass.

        Decorator for registering frame types to their implementing classes.

        :param FrameType frame_types: Frame type(s) to register
        :return: Decorator function
        """

        def decorator(subclass):
            for frame_type in frame_types:
                cls._registry[frame_type] = subclass
            return subclass

        return decorator

    @classmethod
    async def get_frame_class(cls, frame_type: FrameType) -> Type["Frame"]:
        """
        Retrieve Frame class for a given frame type.

        :param FrameType frame_type: Frame type to look up
        :return: Frame class for the given type
        :raises SpopDecodeError: If frame type is not registered
        """
        frame_class = cls._registry.get(frame_type)
        if frame_class is None:
            raise SpopDecodeError(
                f"Unknown frame type {frame_type}",
            )

        return frame_class

    async def encode(self, max_frame_size: int) -> bytes:
        """
        Encode frame type, metadata, and payload to SPOP bytes.

        :param int max_frame_size: Maximum frame size allowed by connection
        :return: Encoded frame bytes
        :raises SpopEncodeError: If encoded frame exceeds max_frame_size
        """
        logger.debug(f"Encoding {self.frame_type.name} frame")

        out = bytearray()
        out.extend(await encode_tiny_int(self.frame_type))
        out.extend(await encode_metadata(self.metadata))

        out.extend(await self.encode_payload())

        frame_len = len(out)
        encoded = bytearray(await encode_frame_len(frame_len)) + out

        if len(encoded) > max_frame_size:
            raise SpopEncodeError(
                f"Total frame size {len(encoded)} exceeds maximum size {max_frame_size}"
            )

        logger.debug(f"Encoded {self.frame_type.name} frame")
        logger.debug(f"frame size: {len(encoded)} bytes (limit: {max_frame_size})")
        return bytes(encoded)

    @classmethod
    async def decode(cls, reader: StreamReader) -> "Frame":
        """
        Decode frame from SPOP byte stream.

        Reads frame length, type, metadata, and payload from stream.

        :param StreamReader reader: AsyncIO stream reader for SPOP connection
        :return: Decoded Frame object
        :raises SpopEOFError: If connection closed at EOF
        :raises SpopDecodeError: If frame decoding fails
        """
        logger.debug("Starting decode frame from stream")

        try:
            len_buf = await reader.readexactly(4)
        except IncompleteReadError:
            if reader.at_eof():
                # If the connections is closed with an EOF - we catch it here. Any other time we hit an EOF/run
                # out of bytes to read is considered abnormal, and we just raise a decode error.
                raise SpopEOFError()

            raise SpopDecodeError(
                "unexpected end of stream reached while decoding frame length",
            )

        # HAProxy sends Frame len as an unencoded UINT32 - can't use data_decoder
        frame_len = await decode_frame_len(len_buf)
        logger.debug(f"Frame length: {frame_len} bytes")

        try:
            frame_buf = await reader.readexactly(frame_len)
        except IncompleteReadError:
            raise SpopDecodeError(
                "unexpected end of stream reached while decoding frame",
            )

        offset = 0  # Set our starting offset at 0

        if len(frame_buf) < offset + 1:
            raise SpopDecodeError(
                "unexpected end of stream identifying frame type",
            )

        try:
            frame_type = FrameType(frame_buf[offset])
        except ValueError:
            raise SpopDecodeError(f"invalid frame type: {frame_buf[offset]}")
        offset += 1

        logger.debug(f"Identified {frame_type.name} frame type from stream")

        metadata, offset = await decode_metadata(frame_buf, offset)

        logger.debug(
            f"Frame metadata: stream_id={metadata.stream_id}, "
            f"frame_id={metadata.frame_id}, FIN={metadata.flags.FIN}, "
            f"ABORT={metadata.flags.ABORT}"
        )

        frame_class = await cls.get_frame_class(frame_type)
        try:
            frame, offset = await frame_class(frame_type, metadata).decode_payload(
                frame_buf, offset, frame_len
            )
        except KeyError as e:
            raise SpopDecodeError(
                f"Not all expected k,v pairs found in {frame_type.name} payload: {e}",
            )

        if offset != frame_len:
            raise SpopDecodeError(
                f"frame offset {offset} does not match frame length {frame_len} - did not consume all bytes"
            )

        logger.debug(f"Decoded {frame_type.name} frame")
        logger.debug(
            f"stream_id={metadata.stream_id}, frame_id={metadata.frame_id}, "
            f"consumed {offset}/{frame_len} bytes"
        )
        return frame

    @classmethod
    async def construct(
        cls, frame_type: FrameType, stream_id: int, frame_id: int, **payload_kwargs
    ) -> "Frame":
        """
        Construct frame from known arguments.

        Used when building response frames for encoding.

        :param FrameType frame_type: Type of frame to construct
        :param int stream_id: Stream identifier
        :param int frame_id: Frame sequence number
        :param payload_kwargs: Frame-specific payload arguments
        :return: Constructed Frame object
        :raises SpoeForgeError: If required payload arguments missing
        """
        frame_class = await cls.get_frame_class(frame_type)

        logger.debug(
            f"Constructing {frame_type.name} frame: "
            f"stream_id={stream_id}, frame_id={frame_id}"
        )

        # SPOP dictates that fragmentation is no longer supported in 2.0+, therefore FIN is always set.
        # ABORT is very rarely if ever used from HAProxy - and Agents never set it themselves so we force it
        # to be false. This can be adjusted in the future if needed.
        metadata = MetaData(
            frame_id=frame_id, stream_id=stream_id, flags=Flags(ABORT=False, FIN=True)
        )

        try:
            frame = await frame_class(frame_type, metadata).construct_payload(
                **payload_kwargs
            )
        except KeyError as e:
            raise SpoeForgeError(
                f"Not all expected k,v pairs found in {frame_type.name} construction: {e}",
            )

        logger.debug(f"Constructed {frame_type.name} frame")
        return frame

    @abstractmethod
    async def encode_payload(self) -> bytes:
        """
        Encode frame-specific payload to bytes.

        Subclasses must implement this to encode their payload structure.

        :return: Encoded payload bytes
        """
        raise NotImplementedError()

    @abstractmethod
    async def decode_payload(
        self, buf: bytes, offset: int, end: int
    ) -> SpoaDec["Frame"]:
        """
        Decode frame-specific payload from bytes.

        Subclasses must implement this to decode their payload and set attributes.

        :param bytes buf: SPOP byte stream to consume from
        :param int offset: Offset to start reading from
        :param int end: Expected end position
        :return: Tuple of (self, adjusted offset)
        """
        raise NotImplementedError()

    @abstractmethod
    async def construct_payload(self, **payload_kwargs) -> "Frame":
        """
        Construct frame payload from keyword arguments.

        Subclasses must implement this to set payload attributes from kwargs.

        :param payload_kwargs: Frame-specific payload arguments
        :return: Self with payload attributes set
        """
        raise NotImplementedError()

    @staticmethod
    def to_spop_list(items: list[str]) -> str:
        """
        Convert list of strings to SPOP comma-separated format.

        :param list[str] items: List of strings to convert
        :return: Comma-separated string
        """
        return ",".join(item.strip() for item in items)

    @staticmethod
    def from_spop_list(items: str) -> list[str]:
        """
        Parse SPOP comma-separated format to list of strings.

        :param str items: Comma-separated string to parse
        :return: List of strings
        """
        return [it for item in items.split(",") if (it := item.strip())]


@Frame.register(FrameType.HAPROXY_HELLO)
class HaproxyHello(Frame):
    """
    HAPROXY-HELLO frame sent by HAProxy to initiate connection.

    Contains HAProxy's protocol version, capabilities, and configuration.
    Agent must respond with AGENT-HELLO.

    Attributes:
        supported_versions: List of SPOP versions HAProxy supports
        max_frame_size: Maximum frame size HAProxy will accept
        capabilities: List of protocol capabilities HAProxy supports
        engine_id: Optional HAProxy engine identifier
        healthcheck: True if this is a healthcheck connection
    """

    supported_versions: list[str]
    max_frame_size: int
    capabilities: list[str]
    engine_id: str = None
    healthcheck: bool = False

    async def encode_payload(self) -> bytes:
        payload = {
            "supported-versions": self.to_spop_list(self.supported_versions),
            "max-frame-size": self.max_frame_size,
            "capabilities": self.to_spop_list(self.capabilities),
            "healthcheck": self.healthcheck,
        }

        if self.engine_id is not None:
            payload["engine-id"] = self.engine_id

        return await encode_kv_list(payload)

    async def decode_payload(
        self, buf: bytes, offset: int, end: int
    ) -> SpoaDec["HaproxyHello"]:
        payload, offset = await decode_kv_list(buf, offset=offset, end=end)

        self.supported_versions = self.from_spop_list(payload["supported-versions"])
        self.max_frame_size = payload["max-frame-size"]
        self.capabilities = self.from_spop_list(payload["capabilities"])
        self.engine_id = payload.get("engine-id")
        self.healthcheck = payload.get("healthcheck", False)

        return self, offset

    async def construct_payload(self, **payload_kwargs) -> "HaproxyHello":
        self.supported_versions = payload_kwargs["supported_versions"]
        self.max_frame_size = payload_kwargs["max_frame_size"]
        self.capabilities = payload_kwargs["capabilities"]
        self.engine_id = payload_kwargs.get("engine_id")
        self.healthcheck = payload_kwargs.get("healthcheck", False)

        return self


@Frame.register(FrameType.AGENT_HELLO)
class AgentHello(Frame):
    """
    AGENT-HELLO frame sent by agent in response to HAPROXY-HELLO.

    Negotiates protocol version, frame size, and capabilities.

    Attributes:
        version: SPOP version agent is using
        max_frame_size: Maximum frame size agent will accept
        capabilities: List of capabilities agent supports
    """

    version: str
    max_frame_size: int
    capabilities: list[str]

    async def encode_payload(self) -> bytes:
        payload = {
            "version": self.version,
            "max-frame-size": self.max_frame_size,
            "capabilities": self.to_spop_list(self.capabilities),
        }

        return await encode_kv_list(payload)

    async def decode_payload(
        self, buf: bytes, offset: int, end: int
    ) -> SpoaDec["AgentHello"]:
        payload, offset = await decode_kv_list(buf, offset=offset, end=end)

        self.version = payload["version"]
        self.max_frame_size = payload["max-frame-size"]
        self.capabilities = self.from_spop_list(payload["capabilities"])

        return self, offset

    async def construct_payload(self, **payload_kwargs) -> "AgentHello":
        self.version = payload_kwargs["version"]
        self.max_frame_size = payload_kwargs["max_frame_size"]
        self.capabilities = payload_kwargs["capabilities"]

        return self


@Frame.register(FrameType.HAPROXY_DISCONNECT, FrameType.AGENT_DISCONNECT)
class Disconnect(Frame):
    """
    Disconnect frame sent to gracefully close connection.

    Can be sent by either HAProxy or Agent. Registered for both frame types
    since the structure is identical.

    Attributes:
        status_code: Disconnect reason code (0 = normal)
        message: Human-readable disconnect message
    """

    status_code: int
    message: str

    async def encode_payload(self) -> bytes:
        payload = {
            "status-code": self.status_code,
            "message": self.message,
        }

        return await encode_kv_list(payload)

    async def decode_payload(
        self, buf: bytes, offset: int, end: int
    ) -> SpoaDec["Disconnect"]:
        payload, offset = await decode_kv_list(buf, offset=offset, end=end)

        self.status_code = payload["status-code"]
        self.message = payload["message"]

        return self, offset

    async def construct_payload(self, **payload_kwargs) -> "Disconnect":
        self.status_code = payload_kwargs["status_code"]
        self.message = payload_kwargs["message"]

        return self


@Frame.register(FrameType.NOTIFY)
class Notify(Frame):
    """
    NOTIFY frame sent by HAProxy containing messages for processing.

    Contains one or more messages with arguments. Agent must respond with ACK.

    Attributes:
        messages: Dict mapping message names to their arguments
                  {message_name: {arg_name: arg_value}}
    """

    messages: Messages

    async def encode_payload(self) -> bytes:
        return await encode_message_list(self.messages)

    async def decode_payload(
        self, buf: bytes, offset: int, end: int
    ) -> SpoaDec["Notify"]:
        self.messages, offset = await decode_list_of_messages(
            buf, offset=offset, end=end
        )

        return self, offset

    async def construct_payload(self, **payload_kwargs) -> "Notify":
        self.messages = payload_kwargs["messages"]

        return self


@Frame.register(FrameType.ACK)
class Ack(Frame):
    """
    ACK frame sent by agent in response to NOTIFY.

    Contains actions (SET_VAR, UNSET_VAR) to be applied in HAProxy.

    Attributes:
        actions: Actions to perform
    """

    actions: list[Action]

    async def encode_payload(self) -> bytes:
        if self.actions is None:
            return bytes()

        return await encode_action_list(self.actions)

    async def decode_payload(self, buf: bytes, offset: int, end: int) -> SpoaDec["Ack"]:
        self.actions, offset = await decode_list_of_actions(buf, offset=offset, end=end)

        return self, offset

    async def construct_payload(self, **payload_kwargs) -> "Ack":
        self.actions = payload_kwargs["actions"]
        return self
