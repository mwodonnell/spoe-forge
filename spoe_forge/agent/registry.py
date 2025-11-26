import asyncio
import logging
from typing import Callable

from spoe_forge.agent.context import AgentContext
from spoe_forge.agent.exceptions import SpoeAgentError
from spoe_forge.spop.spop_types import SpoaDataType, Action

logger = logging.getLogger(__name__)

MessageHandlerFunc = Callable[[AgentContext], list[Action]]


class AgentRegistry:
    """
    Internal registry mapping message names to handler functions.

    Note: Users don't interact with this directly - it's used by the Agent class.
    """

    def __init__(self):
        """Initialize a new agent registry."""
        self._handlers: dict[str, MessageHandlerFunc] = {}
        self._validation_cache: dict[str, bool] = {}

    def register(self, message_name: str, handler: MessageHandlerFunc) -> None:
        """
        Register a handler for a message type.

        :param str message_name: Message name to handle
        :param MessageHandlerFunc handler: User-defined handler function
        """
        if message_name in self._handlers:
            logger.warning(f"Overwriting existing handler for message '{message_name}'")

        self._handlers[message_name] = handler
        logger.debug(f"Registered handler for message '{message_name}'")

    async def handle_message(
        self, message: str, args: dict[str, SpoaDataType]
    ) -> list[Action]:
        """
        Route a message to its registered handler.

        Wraps synchronous handlers with asyncio.to_thread for async compatibility.

        :param str message: Message name to handle
        :param dict[str, SpoaDataType] args: Message arguments
        :return: List of actions from handler (empty if no handler registered)
        :raises SpoeAgentError: If handler raises an exception
        """
        handler = self._handlers.get(message)

        if handler is None:
            logger.warning(f"No handler registered for message '{message}'")
            return []

        ctx = AgentContext(message, args)
        try:
            return await asyncio.to_thread(handler, ctx)
        except Exception as e:
            logger.error(
                f"Error in handler for message '{message}': {e}", exc_info=True
            )
            # Convert to our own error - will be caught in our own handlers to
            # cause a graceful kill of the connection
            raise SpoeAgentError(e)
