import asyncio
import logging
from asyncio import StreamReader
from asyncio import StreamWriter
from typing import Callable
from typing import Awaitable

from spoe_forge.exception import SpoeForgeError
from spoe_forge.server.configuration import ServerConfiguration
from spoe_forge.server.constants import DisconnectCode
from spoe_forge.server.exceptions import CloseConnection
from spoe_forge.spop.constants import FrameType
from spoe_forge.spop.exception import SpopEncodeError
from spoe_forge.spop.exception import SpopEOFError
from spoe_forge.spop.exception import SpopFrameTooBigError
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
        :return: True if frame was sent, False if the stream is closing
        :raises SpopEncodeError: If the frame fails to encode
        :raises SpopFrameTooBigError: If the frame exceeds the negotiated size
        """
        if self.writer.is_closing():
            logger.warning(
                f"Could not send frame {frame.frame_type.name} - stream closed"
            )
            return False

        self.writer.write(frame.encode(self.config.max_frame_size))

        await self.writer.drain()
        return True

    async def send_disconnect(self, status_code: DisconnectCode, message: str) -> bool:
        """
        Send AGENT_DISCONNECT frame to HAProxy.

        :param DisconnectCode status_code: Disconnect reason code
        :param str message: Human-readable disconnect message
        :return: True if disconnect frame was sent successfully, False otherwise
        """
        err_frame = Frame.construct(
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
        frame = await Frame.decode(self.reader, self.config.max_frame_size)
        if not isinstance(frame, HaproxyHello):
            await self.send_disconnect_on_error(
                status_code=DisconnectCode.INVALID_FRAME_RECEIVED,
                message=f"Expected HAPROXY-HELLO, received {frame.frame_type.name}",
            )
            return False

        self.config.negotiate_server_compatibility(
            frame.supported_versions, frame.max_frame_size, frame.capabilities
        )

        if not self.config.is_compatible:
            await self.send_disconnect_on_error(
                status_code=DisconnectCode.SERVER_INCOMPATIBLE,
                message="Handshake failed to find compatibility.",
            )
            return False

        agent_hello = Frame.construct(
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

    async def _process_notify(self, frame: Notify, slots: asyncio.Semaphore) -> None:
        """
        Run the agent handler for one NOTIFY frame and send its ACK.

        Handler output that fails to encode (oversized or unencodable action
        values) is logged and answered with an empty ACK - the same forgiving
        policy as handler exceptions, containing the failure to this stream.

        Sending directly from the task is safe: the frame is fully encoded and
        written with a single writer.write() call, so concurrent tasks cannot
        interleave frame bytes.

        :param Notify frame: Decoded NOTIFY frame to process
        :param asyncio.Semaphore slots: Concurrency slot to release when done
        """
        try:
            actions = await self.notify_handler(frame.messages)

            ack = Frame.construct(
                FrameType.ACK,
                stream_id=frame.metadata.stream_id,
                frame_id=frame.metadata.frame_id,
                actions=actions,
            )

            try:
                await self.send_frame(ack)
            except (SpopEncodeError, SpopFrameTooBigError) as e:
                logger.error(
                    f"Failed to encode ACK for stream {frame.metadata.stream_id}: {e} - sending empty ACK"
                )

                empty_ack = Frame.construct(
                    FrameType.ACK,
                    stream_id=frame.metadata.stream_id,
                    frame_id=frame.metadata.frame_id,
                    actions=[],
                )
                await self.send_frame(empty_ack)
        finally:
            slots.release()

    async def _read_frames(
        self, tg: asyncio.TaskGroup, slots: asyncio.Semaphore
    ) -> None:
        """
        Read frames until the connection ends, dispatching NOTIFYs as tasks.

        Acquires a concurrency slot before each read so that at capacity the
        loop stops reading and TCP flow control pushes back on HAProxy.

        :param asyncio.TaskGroup tg: Task group owning the NOTIFY tasks
        :param asyncio.Semaphore slots: Per-connection concurrency bound
        :raises CloseConnection: When the connection should close gracefully
        """
        while True:
            await slots.acquire()

            try:
                frame = await Frame.decode(self.reader, self.config.max_frame_size)
            except SpopEOFError:
                logger.debug("Stream disconnected with EOF")
                raise CloseConnection()

            if isinstance(frame, Disconnect):
                if frame.status_code == DisconnectCode.NORMAL:
                    logger.debug("Connection closed gracefully by HAProxy")
                else:
                    logger.warning(
                        f"Received HAPROXY_DISCONNECT: {frame.message} (status: {frame.status_code})"
                    )

                await self.send_disconnect(
                    status_code=DisconnectCode.NORMAL,
                    message="Disconnecting normally",
                )
                raise CloseConnection()

            if not isinstance(frame, Notify):
                await self.send_disconnect_on_error(
                    status_code=DisconnectCode.INVALID_FRAME_RECEIVED,
                    message=f"Expected NOTIFY or HAPROXY_DISCONNECT, received {frame.frame_type.name}",
                )
                raise CloseConnection()

            tg.create_task(self._process_notify(frame, slots))

    async def core_handler(self):
        """
        Main connection lifecycle handler.

        Executes handshake followed by the NOTIFY/ACK loop until the connection
        closes. When pipelining is negotiated, NOTIFY frames are processed
        concurrently (bounded by max_concurrent_frames) and ACKs are sent in
        completion order, which SPOP explicitly allows; otherwise concurrency
        is 1, preserving strict serial behavior. A protocol error in any task
        cancels the rest and disconnects; disconnect/EOF cancels in-flight
        tasks rather than draining them.
        """
        try:
            async with asyncio.TaskGroup() as tg:
                if not await self.handle_handshake():
                    raise CloseConnection()

                limit = (
                    self.config.max_concurrent_frames
                    if "pipelining" in self.config.capabilities
                    else 1
                )
                await self._read_frames(tg, asyncio.Semaphore(limit))

        except* CloseConnection:
            pass

        except* SpopFrameTooBigError as eg:
            await self.send_disconnect_on_error(
                status_code=DisconnectCode.FRAME_TOO_BIG,
                message=str(eg.exceptions[0]),
            )

        except* SpoeForgeError as eg:
            if not await self.send_disconnect_on_error(
                status_code=DisconnectCode.PROTOCOL_ERROR,
                message=str(eg.exceptions[0]),
            ):
                logger.error(
                    f"Failed to send disconnect on error while handling: {eg.exceptions[0]}",
                    exc_info=True,
                )

        except* ConnectionResetError:
            # Expected case from HAProxy - we treat it as a graceful disconnect
            logger.debug("Connection reset by HAProxy")

        try:
            await self.close_connection()
        except ConnectionResetError:
            logger.debug("Connection reset by HAProxy while closing")
