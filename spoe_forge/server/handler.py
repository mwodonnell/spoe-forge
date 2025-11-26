import logging
from asyncio import StreamReader
from asyncio import StreamWriter
from typing import Callable
from typing import Awaitable

from spoe_forge.exception import SpoeForgeError
from spoe_forge.server.configuration import ServerConfiguration
from spoe_forge.server.constants import DisconnectCode
from spoe_forge.spop.constants import FrameType
from spoe_forge.spop.exception import SpopEOFError
from spoe_forge.spop.frame import Disconnect
from spoe_forge.spop.frame import Frame
from spoe_forge.spop.frame import HaproxyHello
from spoe_forge.spop.frame import Notify
from spoe_forge.spop.spop_types import Action, Messages

logger = logging.getLogger(__name__)


class ForgeHandler:
    """
    Handles SPOP protocol lifecycle for a single connection.

    Manages handshake, NOTIFY/ACK cycles, and disconnection for one HAProxy connection.
    """

    def __init__(
        self,
        notify_handler: Callable[[Messages], Awaitable[list[Action]]],
        config: ServerConfiguration,
        reader: StreamReader,
        writer: StreamWriter,
    ):
        """
        Initialize connection handler.

        :param notify_handler: Callback from Forge to process Messages into Actions
        :param ServerConfiguration config: Configuration for this connection
        :param StreamReader reader: AsyncIO stream reader for connection
        :param StreamWriter writer: AsyncIO stream writer for connection
        """
        self.notify_handler = notify_handler
        self.config = config
        self.reader = reader
        self.writer = writer

    async def close_connection(self):
        """Close the connection stream and wait for it to close."""
        if not self.writer.is_closing():
            self.writer.close()

        await self.writer.wait_closed()
        logger.debug("Stream disconnected")

    async def send_frame(self, frame: Frame) -> bool:
        """
        Encode and send a frame to HAProxy.

        :param Frame frame: Frame to encode and send
        :return: True if frame was sent successfully, False otherwise
        """
        if self.writer.is_closing():
            logger.warning(
                f"Could not send frame {frame.frame_type.name} - stream closed"
            )
            return False

        try:
            self.writer.write(await frame.encode(self.config.max_frame_size))
        except SpoeForgeError as e:
            logger.warning(
                f"Failed to write frame to stream - {frame.frame_type.name} - {e}"
            )
            return False

        await self.writer.drain()
        return True

    async def send_disconnect(self, status_code: DisconnectCode, message: str) -> bool:
        """
        Send AGENT_DISCONNECT frame to HAProxy.

        :param DisconnectCode status_code: Disconnect reason code
        :param str message: Human-readable disconnect message
        :return: True if disconnect frame was sent successfully, False otherwise
        """
        err_frame = await Frame.construct(
            FrameType.AGENT_DISCONNECT,
            stream_id=0,
            frame_id=0,
            status_code=status_code,
            message=message,
        )

        return await self.send_frame(err_frame)

    async def send_disconnect_on_error(
        self, status_code: DisconnectCode, message: str
    ) -> bool:
        """
        Send AGENT_DISCONNECT frame and log as error.

        :param DisconnectCode status_code: Disconnect reason code
        :param str message: Human-readable disconnect message
        :return: True if disconnect frame was sent successfully, False otherwise
        """
        logger.error(
            f"SPOA server encountered an error, disconnecting: {status_code.name}: {message}"
        )
        return await self.send_disconnect(status_code, message)

    async def handle_handshake(self) -> bool:
        """
        Handle SPOP handshake phase with HAProxy.

        Receives HAPROXY_HELLO, negotiates compatibility, and sends AGENT_HELLO.
        Closes connection immediately if healthcheck flag is set.

        :return: True if handshake succeeded and processing should continue, False otherwise
        """
        frame = await Frame.decode(self.reader)
        if not isinstance(frame, HaproxyHello):
            await self.send_disconnect_on_error(
                status_code=DisconnectCode.INVALID_FRAME_RECEIVED,
                message=f"Expected HAPROXY-HELLO, received {frame.frame_type.name}",
            )
            return False

        await self.config.negotiate_server_compatibility(
            frame.supported_versions, frame.max_frame_size, frame.capabilities
        )

        if not self.config.is_compatible:
            await self.send_disconnect_on_error(
                status_code=DisconnectCode.SERVER_INCOMPATIBLE,
                message="Handshake failed to find compatibility.",
            )
            return False

        agent_hello = await Frame.construct(
            FrameType.AGENT_HELLO,
            stream_id=0,
            frame_id=0,
            version=self.config.version,
            max_frame_size=self.config.max_frame_size,
            capabilities=self.config.capabilities,
        )

        res = await self.send_frame(agent_hello)
        if frame.healthcheck:
            # Health check means we close the connection immediately after sending AGENT-HELLO
            logger.debug("Healthcheck connection - closing after AGENT-HELLO")
            return False

        if res:
            logger.debug(
                f"Connection established - SPOP {self.config.version}, "
                f"frame_size={self.config.max_frame_size}, "
                f"capabilities={','.join(self.config.capabilities)}"
            )

        return res

    async def handle_notify_cycle(self) -> bool:
        """
        Handle a single NOTIFY/ACK cycle or HAPROXY_DISCONNECT.

        Receives NOTIFY frame, calls agent to process messages, and sends ACK with actions.
        Also handles graceful HAPROXY_DISCONNECT frames and EOF conditions.

        :return: True if cycle completed successfully, False if connection should close
        """
        try:
            frame = await Frame.decode(self.reader)
        except SpopEOFError:
            logger.debug("Stream disconnected with EOF")
            return False

        # Handle graceful disconnect from HAProxy
        if isinstance(frame, Disconnect):
            if frame.status_code == DisconnectCode.NORMAL:
                logger.debug("Connection closed gracefully by HAProxy")
            else:
                logger.warning(
                    f"Received HAPROXY_DISCONNECT: {frame.message} (status: {frame.status_code})"
                )

            # Respond with AGENT_DISCONNECT
            await self.send_disconnect(
                status_code=DisconnectCode.NORMAL,
                message="Disconnecting normally",
            )
            return False

        if not isinstance(frame, Notify):
            await self.send_disconnect_on_error(
                status_code=DisconnectCode.INVALID_FRAME_RECEIVED,
                message=f"Expected NOTIFY or HAPROXY_DISCONNECT, received {frame.frame_type.name}",
            )
            return False

        actions = await self.notify_handler(frame.messages)

        ack = await Frame.construct(
            FrameType.ACK,
            stream_id=frame.metadata.stream_id,
            frame_id=frame.metadata.frame_id,
            actions=actions,
        )

        return await self.send_frame(ack)

    async def core_handler(self):
        """
        Main connection lifecycle handler.

        Executes handshake followed by NOTIFY/ACK processing loop until connection closes.
        Handles protocol errors and connection resets gracefully.
        """
        try:
            if not await self.handle_handshake():
                await self.close_connection()
                return

            while True:
                if not await self.handle_notify_cycle():
                    await self.close_connection()
                    break

        except SpoeForgeError as e:
            if not await self.send_disconnect_on_error(
                status_code=DisconnectCode.PROTOCOL_ERROR,
                message=str(e),
            ):
                logger.error(
                    f"Failed to send disconnect on error while handling: {str(e)}",
                    exc_info=True,
                )

            await self.close_connection()

        except ConnectionResetError:
            # Expected case from HAProxy - we treat it as a graceful disconnect
            logger.debug("Connection reset by HAProxy")
