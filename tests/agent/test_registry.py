from unittest.mock import patch

import pytest
import ipaddress

from spoe_forge.agent.context import AgentContext
from spoe_forge.agent.exceptions import SpoeAgentError
from spoe_forge.agent.registry import AgentRegistry
from spoe_forge.spop.constants import ActionScope
from spoe_forge.spop.spop_types import SetVarAction
from spoe_forge.spop.spop_types import UnsetVarAction


def test_registry_initialization():
    registry = AgentRegistry()

    assert registry._handlers == {}


def test_register_adds_handler():
    registry = AgentRegistry()

    def handler(ctx: AgentContext):
        return []

    registry.register("test-message", handler)

    assert "test-message" in registry._handlers
    assert registry._handlers["test-message"] == handler


def test_register_multiple_handlers():
    registry = AgentRegistry()

    def handler1(ctx: AgentContext):
        return []

    def handler2(ctx: AgentContext):
        return []

    registry.register("message1", handler1)
    registry.register("message2", handler2)

    assert len(registry._handlers) == 2
    assert registry._handlers["message1"] == handler1
    assert registry._handlers["message2"] == handler2


def test_register_overwrites_existing_handler():
    registry = AgentRegistry()

    def handler1(ctx: AgentContext):
        return []

    def handler2(ctx: AgentContext):
        return []

    registry.register("test-message", handler1)

    with patch("spoe_forge.agent.registry.logger") as mock_logger:
        registry.register("test-message", handler2)
        mock_logger.warning.assert_called_once()
        assert "Overwriting existing handler" in mock_logger.warning.call_args[0][0]

    assert registry._handlers["test-message"] == handler2


def test_register_logs_debug_message():
    registry = AgentRegistry()

    def handler(ctx: AgentContext):
        return []

    with patch("spoe_forge.agent.registry.logger") as mock_logger:
        registry.register("test-message", handler)
        mock_logger.debug.assert_called_once()
        assert "Registered handler" in mock_logger.debug.call_args[0][0]


@pytest.mark.asyncio
async def test_handle_message_calls_registered_handler():
    registry = AgentRegistry()

    def handler(ctx: AgentContext):
        return [SetVarAction(scope=ActionScope.SESSION, name="test", value=42)]

    registry.register("test-message", handler)

    result = await registry.handle_message("test-message", {"arg": "value"})

    assert len(result) == 1
    assert isinstance(result[0], SetVarAction)
    assert result[0].name == "test"
    assert result[0].value == 42


@pytest.mark.asyncio
async def test_handle_message_passes_context_to_handler():
    registry = AgentRegistry()
    captured_context = None

    def handler(ctx: AgentContext):
        nonlocal captured_context
        captured_context = ctx
        return []

    registry.register("test-message", handler)

    args = {"ip": "192.168.1.1", "port": 8080}
    await registry.handle_message("test-message", args)

    assert captured_context is not None
    assert captured_context._message == "test-message"
    assert captured_context._args == args


@pytest.mark.asyncio
async def test_handle_message_returns_empty_list_when_no_handler():
    registry = AgentRegistry()

    with patch("spoe_forge.agent.registry.logger") as mock_logger:
        result = await registry.handle_message("unregistered-message", {})

        assert result == []
        mock_logger.warning.assert_called_once()
        assert "No handler registered" in mock_logger.warning.call_args[0][0]


@pytest.mark.asyncio
async def test_handle_message_runs_handler_in_thread():
    registry = AgentRegistry()

    def handler(ctx: AgentContext):
        return []

    registry.register("test-message", handler)

    with patch("spoe_forge.agent.registry.asyncio.to_thread") as mock_to_thread:
        mock_to_thread.return_value = []

        await registry.handle_message("test-message", {})

        mock_to_thread.assert_called_once()
        assert mock_to_thread.call_args[0][0] == handler
        assert isinstance(mock_to_thread.call_args[0][1], AgentContext)


@pytest.mark.asyncio
async def test_handle_message_wraps_handler_exceptions():
    registry = AgentRegistry()

    def handler(ctx: AgentContext):
        raise ValueError("Test error")

    registry.register("test-message", handler)

    with patch("spoe_forge.agent.registry.logger") as mock_logger:
        with pytest.raises(SpoeAgentError):
            await registry.handle_message("test-message", {})

        mock_logger.error.assert_called_once()
        assert "Error in handler" in mock_logger.error.call_args[0][0]


@pytest.mark.asyncio
async def test_handle_message_preserves_original_exception():
    registry = AgentRegistry()

    original_error = ValueError("Original error message")

    def handler(ctx: AgentContext):
        raise original_error

    registry.register("test-message", handler)

    with pytest.raises(SpoeAgentError) as exc_info:
        await registry.handle_message("test-message", {})

    assert exc_info.value.args[0] == original_error


@pytest.mark.asyncio
async def test_handle_message_with_empty_action_list():
    registry = AgentRegistry()

    def handler(ctx: AgentContext):
        return []

    registry.register("test-message", handler)

    result = await registry.handle_message("test-message", {})

    assert result == []


@pytest.mark.asyncio
async def test_handle_message_with_multiple_actions():
    registry = AgentRegistry()

    def handler(ctx: AgentContext):
        return [
            SetVarAction(scope=ActionScope.SESSION, name="var1", value=1),
            SetVarAction(scope=ActionScope.REQUEST, name="var2", value=2),
            UnsetVarAction(scope=ActionScope.SESSION, name="var3"),
        ]

    registry.register("test-message", handler)

    result = await registry.handle_message("test-message", {})

    assert len(result) == 3
    assert isinstance(result[0], SetVarAction)
    assert isinstance(result[1], SetVarAction)
    assert isinstance(result[2], UnsetVarAction)


@pytest.mark.asyncio
async def test_handle_message_handler_can_access_args():
    registry = AgentRegistry()

    def handler(ctx: AgentContext):
        ip = ctx.get_arg("ip")
        port = ctx.get_arg("port")
        return [
            SetVarAction(
                scope=ActionScope.SESSION, name="client_ip", value=ip or "unknown"
            ),
            SetVarAction(
                scope=ActionScope.SESSION, name="client_port", value=port or 0
            ),
        ]

    registry.register("test-message", handler)

    result = await registry.handle_message(
        "test-message", {"ip": "192.168.1.1", "port": 8080}
    )

    assert len(result) == 2
    assert result[0].value == "192.168.1.1"
    assert result[1].value == 8080


@pytest.mark.asyncio
async def test_handle_message_with_complex_args():
    registry = AgentRegistry()

    def handler(ctx: AgentContext):
        return [
            SetVarAction(
                scope=ActionScope.SESSION,
                name="has_ip",
                value=ctx.has_arg("ip"),
            )
        ]

    registry.register("test-message", handler)

    args = {
        "ip": ipaddress.IPv4Address("192.168.1.1"),
        "binary": b"\x00\x01\x02",
        "flag": True,
    }

    result = await registry.handle_message("test-message", args)

    assert len(result) == 1
    assert result[0].value is True


@pytest.mark.asyncio
async def test_multiple_messages_independent():
    registry = AgentRegistry()

    def handler1(ctx: AgentContext):
        return [SetVarAction(scope=ActionScope.SESSION, name="h1", value=1)]

    def handler2(ctx: AgentContext):
        return [SetVarAction(scope=ActionScope.SESSION, name="h2", value=2)]

    registry.register("message1", handler1)
    registry.register("message2", handler2)

    result1 = await registry.handle_message("message1", {})
    result2 = await registry.handle_message("message2", {})

    assert result1[0].name == "h1"
    assert result2[0].name == "h2"


@pytest.mark.asyncio
async def test_handler_can_return_different_action_types():
    registry = AgentRegistry()

    def handler(ctx: AgentContext):
        should_set = ctx.get_arg("set", default=True)
        if should_set:
            return [SetVarAction(scope=ActionScope.SESSION, name="var", value=42)]
        else:
            return [UnsetVarAction(scope=ActionScope.SESSION, name="var")]

    registry.register("test-message", handler)

    result1 = await registry.handle_message("test-message", {"set": True})
    result2 = await registry.handle_message("test-message", {"set": False})

    assert isinstance(result1[0], SetVarAction)
    assert isinstance(result2[0], UnsetVarAction)


@pytest.mark.asyncio
async def test_registry_handles_message_names_case_sensitive():
    registry = AgentRegistry()

    def handler(ctx: AgentContext):
        return [SetVarAction(scope=ActionScope.SESSION, name="test", value=1)]

    registry.register("Message", handler)

    result1 = await registry.handle_message("Message", {})
    assert len(result1) == 1

    with patch("spoe_forge.agent.registry.logger"):
        result2 = await registry.handle_message("message", {})
        assert result2 == []


@pytest.mark.asyncio
async def test_handler_exception_includes_message_name():
    registry = AgentRegistry()

    def handler(ctx: AgentContext):
        raise RuntimeError("Handler failed")

    registry.register("failing-message", handler)

    with patch("spoe_forge.agent.registry.logger") as mock_logger:
        with pytest.raises(SpoeAgentError):
            await registry.handle_message("failing-message", {})

        error_call = mock_logger.error.call_args[0][0]
        assert "failing-message" in error_call
