import asyncio
import logging
from asyncio import StreamReader
from asyncio import StreamWriter

from spoe_forge.agent.agent import Agent
from spoe_forge.log import init_logging
from spoe_forge.server.configuration import ServerConfiguration
from spoe_forge.server.constants import DEFAULT_MAX_FRAME_SIZE
from spoe_forge.server.handler import ForgeHandler

init_logging()

logger = logging.getLogger("spoe-forge")


class SpoeForge:
    """
    Main SPOE server that accepts connections and delegates to handlers.

    Creates ForgeHandler instances for each connection to manage SPOP protocol.
    """

    def __init__(self, agent: Agent, max_frame_size: int = DEFAULT_MAX_FRAME_SIZE):
        """
        Initialize SPOE server with agent and frame size limit.

        :param Agent agent: Agent instance containing message handlers
        :param int max_frame_size: Maximum frame size to negotiate with HAProxy
        """
        self._agent = agent
        self._max_frame_size = max_frame_size

    async def _handler(self, reader: StreamReader, writer: StreamWriter):
        """
        Handle incoming connection by creating ForgeHandler instance.

        :param StreamReader reader: AsyncIO stream reader for connection
        :param StreamWriter writer: AsyncIO stream writer for connection
        """
        # Always create a fresh config object as we need to negotiate compatibility on every connection
        config = ServerConfiguration(max_frame_size=self._max_frame_size)
        handler = ForgeHandler(self._agent, config, reader, writer)

        await handler.core_handler()

    async def _start_server(self, host: str, port: int):
        """
        Start AsyncIO server and listen for connections.

        :param str host: Host address to bind to
        :param int port: Port to listen on
        """
        server = await asyncio.start_server(self._handler, host, port)
        logger.info(f"SPOE Forge listening on {host}:{port}")
        async with server:
            await server.serve_forever()

    def run(self, host: str, port: int) -> None:
        """
        Start the SPOE Forge server (blocking).

        Runs the AsyncIO event loop until interrupted.

        :param str host: Host address to bind to
        :param int port: Port to listen on
        """
        asyncio.run(self._start_server(host, port))
