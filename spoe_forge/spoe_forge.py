import asyncio
from asyncio import StreamReader
from asyncio import StreamWriter
from logging import Logger
from functools import cached_property
from typing import Callable

from spoe_forge.agent.exceptions import SpoeAgentError

from spoe_forge.log import create_logger
from spoe_forge.server.configuration import ServerConfiguration
from spoe_forge.server.constants import DEFAULT_MAX_FRAME_SIZE
from spoe_forge.server.handler import ForgeHandler
from spoe_forge.spop.spop_types import Action
from spoe_forge.spop.spop_types import Messages
from spoe_forge.agent.registry import AgentRegistry
from spoe_forge.agent.registry import MessageHandlerFunc


class SpoeForge:
    """
    User-facing API for creating a Forge Server and SPOE agents.

    Example:
        agent = SpoeForge(name="my-agent")

        @agent.message("check-ip")
        def check_ip(ctx: AgentContext) -> list[Action]:
            ip = ctx.get_arg("src")
            return [SetVarAction(scope=ActionScope.SESSION, name="ip_score", value=95)]

        agent.run()
    """

    def __init__(
        self,
        name: str,
        max_frame_size: int = DEFAULT_MAX_FRAME_SIZE,
        debug: bool = False,
    ):
        """
        Create a new agent.

        :param name: Agent name (for logging/debugging)
        """
        self.name = name
        self._registry = AgentRegistry()
        self._max_frame_size = max_frame_size
        self._debug = debug

    @cached_property
    def _logger(self) -> Logger:
        return create_logger(self._debug)

    def message(
        self, message: str
    ) -> Callable[[MessageHandlerFunc], MessageHandlerFunc]:
        """
        Decorator to register a message handler.

        :param message: The SPOE message to handle (as defined in HAProxy config)
        :return: Decorated function

        Example:
            @agent.message("check-client-ip")
            def handle_ip_check(ctx: AgentContext) -> list[Action]:
                ip = ctx.get_arg("src")
                # ... process IP
                return [SetVarAction(...)]
        """

        def decorator(func: MessageHandlerFunc) -> MessageHandlerFunc:
            self._registry.register(message, func)
            self._logger.debug(f"Registered handler for {message}")
            return func

        return decorator

    async def _notify_handler(self, messages: Messages) -> list[Action]:
        """
        Process NOTIFY frame messages and return aggregated actions.

        Called by server layer when NOTIFY frame is received. Routes each message
        to its registered handler and collects actions.

        :param messages: Messages from NOTIFY frame
        :return: Aggregated list of actions from all handlers
        :raises SpoeAgentError: If handler returns invalid type
        """
        actions = []

        for message, args in messages.items():
            handler_actions = await self._registry.handle_message(message, args)

            if handler_actions is None:
                handler_actions = []

            if not isinstance(handler_actions, list):
                raise SpoeAgentError(
                    f"Handler for message '{message}' did not return list or None. Received {type(handler_actions)}"
                )

            self._logger.info(
                f"{self.name} handled '{message}', returned {len(handler_actions)} action(s)"
            )
            if handler_actions:
                actions.extend(handler_actions)

        return actions

    async def _handler(self, reader: StreamReader, writer: StreamWriter) -> None:
        """
        Handle incoming connection by creating ForgeHandler instance.

        :param StreamReader reader: AsyncIO stream reader for connection
        :param StreamWriter writer: AsyncIO stream writer for connection
        """
        # Always create a fresh config object as we need to negotiate compatibility on every connection
        config = ServerConfiguration(max_frame_size=self._max_frame_size)
        handler = ForgeHandler(self._notify_handler, config, reader, writer)

        await handler.core_handler()

    async def _start_server(self, host: str, port: int) -> None:
        """
        Start AsyncIO server and listen for connections.

        :param str host: Host address to bind to
        :param int port: Port to listen on
        """
        server = await asyncio.start_server(self._handler, host, port)
        self._logger.info(f"SPOE Forge listening on {host}:{port}")

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
