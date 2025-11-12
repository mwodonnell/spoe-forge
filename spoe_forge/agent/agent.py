import logging
from typing import Callable

from spoe_forge.agent.exceptions import SpoeAgentError
from spoe_forge.spop.spop_types import Action
from spoe_forge.agent.context import AgentContext
from spoe_forge.agent.registry import AgentRegistry
from spoe_forge.spop.spop_types import SpoaDataType

logger = logging.getLogger("spoe_forge.agent")
MessageHandlerFunc = Callable[[AgentContext], list[Action]]


class Agent:
    """
    User-facing API for creating SPOA agents.

    Example:
        agent = Agent(name="my-agent")

        @agent.message("check-ip")
        def check_ip(ctx: AgentContext) -> list[Action]:
            ip = ctx.get_arg("src")
            return [SetVarAction(scope=ActionScope.SESSION, name="ip_score", value=95)]
    """

    def __init__(self, name: str):
        """
        Create a new agent.

        :param name: Agent name (for logging/debugging)
        """
        self.name = name
        self._registry = AgentRegistry()

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
            return func

        logger.debug(f"Registered handler for {message}")
        return decorator

    async def handle_notify(
        self, messages: dict[str, dict[str, SpoaDataType]]
    ) -> list[Action]:
        """
        Process NOTIFY frame messages and return aggregated actions.

        Called by server layer when NOTIFY frame is received. Routes each message
        to its registered handler and collects actions.

        :param dict[str, dict[str, SpoaDataType]] messages: Messages from NOTIFY frame
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

            logger.info(
                f"{self.name} handled '{message}', returned {len(handler_actions)} action(s)"
            )
            if handler_actions:
                actions.extend(handler_actions)

        return actions
